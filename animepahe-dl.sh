#!/usr/bin/env bash
# KOYEB VERSION: Node.js Decryption + Cloudscraper Bypass

set -e
set -u

# Setup Variables
_HOST="https://animepahe.si"
_ANIME_URL="$_HOST/anime"
_API_URL="$_HOST/api"
_REFERER_URL="https://kwik.cx/"
_SCRIPT_PATH=$(dirname "$(realpath "$0")")
_ANIME_LIST_FILE="$_SCRIPT_PATH/anime.list"
_SOURCE_FILE=".source.json"

# Tools
_JQ="jq"
_NODE="node"
_YTDLP="yt-dlp"

# 🟢 HELPER: Use Python Cloudscraper to get HTML (Bypasses Cloudflare)
bypass_get() {
    python3 bypass.py "$1"
}

# Standard Curl for non-protected pages
get() {
    curl -sS -L "$1" \
        -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)" \
        --compressed
}

search_anime() {
    # $1: anime name query
    local d
    d="$(get "$_HOST/api?m=search&q=${1// /%20}")"
    # Return the first result's session ID and title
    echo "$d" | "$_JQ" -r '.data[0] | "\(.session)|\(.title)"'
}

get_episode_page() {
    # $1: session_id, $2: page
    get "${_API_URL}?m=release&id=${1}&sort=episode_asc&page=${2}"
}

# Find the Episode Session ID
get_episode_session() {
    # $1: anime_session, $2: episode_number
    # We loop through pages to find the episode (simplified)
    local page=1
    local last_page=1
    local data
    
    # Check first page
    data=$(get_episode_page "$1" "$page")
    last_page=$(echo "$data" | "$_JQ" -r '.last_page')
    
    # Quick check in page 1
    local ep_session
    ep_session=$(echo "$data" | "$_JQ" -r ".data[] | select(.episode==\"$2\") | .session")
    
    if [[ -n "$ep_session" ]]; then
        echo "$ep_session"
        return
    fi

    # If not in page 1, check others
    if [[ "$last_page" -gt 1 ]]; then
        for i in $(seq 2 "$last_page"); do
            data=$(get_episode_page "$1" "$i")
            ep_session=$(echo "$data" | "$_JQ" -r ".data[] | select(.episode==\"$2\") | .session")
            if [[ -n "$ep_session" ]]; then
                echo "$ep_session"
                return
            fi
        done
    fi
}

get_kwik_link() {
    # $1: anime_slug, $2: ep_session
    # Get the player page
    local html
    html=$(get "${_HOST}/play/${1}/${2}")
    
    # Extract Kwik Link for 360p (or fallback)
    local link
    # Try to find 360p specifically
    link=$(echo "$html" | grep 'data-resolution="360"' | grep -o 'https://kwik.cx[^"]*')
    
    # Fallback to any Kwik link if 360p missing
    if [[ -z "$link" ]]; then
        link=$(echo "$html" | grep -o 'https://kwik.cx[^"]*' | head -n 1)
    fi
    echo "$link"
}

extract_m3u8() {
    # $1: Kwik Link
    # 🟢 USE PYTHON BYPASS HERE
    local html
    html=$(bypass_get "$1")

    # Extract the obfuscated JS
    local js
    js=$(echo "$html" | grep "<script>eval(" | awk -F 'script>' '{print $2}' | sed -E 's/document/process/g; s/querySelector/exit/g; s/eval\(/console.log\(/g')

    if [[ -z "$js" ]]; then
        echo "ERROR: Could not find JS" >&2
        echo "$html" >&2
        return 1
    fi

    # Use Node to de-obfuscate
    local decoded
    decoded=$("$_NODE" -e "$js")

    # Extract the .m3u8 link
    echo "$decoded" | grep -o "https://.*\.m3u8"
}

main() {
    local anime_name=""
    local episode=""
    
    # Parse Args
    while getopts ":a:e:r:" opt; do
        case $opt in
            a) anime_name="$OPTARG" ;;
            e) episode="$OPTARG" ;;
            *) ;;
        esac
    done

    echo "[INFO] Searching for: $anime_name"
    local search_res
    search_res=$(search_anime "$anime_name")
    
    local anime_session="${search_res%%|*}"
    local anime_title="${search_res#*|}"
    
    if [[ "$anime_session" == "null" || -z "$anime_session" ]]; then
        echo "[ERROR] Anime not found"
        exit 1
    fi
    
    echo "[INFO] Found: $anime_title ($anime_session)"
    
    echo "[INFO] Finding Episode $episode..."
    local ep_session
    ep_session=$(get_episode_session "$anime_session" "$episode")
    
    if [[ -z "$ep_session" ]]; then
        echo "[ERROR] Episode $episode not found"
        exit 1
    fi

    echo "[INFO] Getting Stream Link..."
    # The slug for play url is actually the anime_session in API v2 context usually, 
    # but let's assume the session ID works for the URL construction.
    # Note: AnimePahe URL structure: /play/{anime_uuid}/{episode_session}
    
    local kwik_link
    kwik_link=$(get_kwik_link "$anime_session" "$ep_session")
    
    if [[ -z "$kwik_link" ]]; then
        echo "[ERROR] Could not find Kwik Link"
        exit 1
    fi
    echo "[INFO] Kwik Link: $kwik_link"
    
    echo "[INFO] Bypassing Cloudflare & Decrypting..."
    local stream_url
    stream_url=$(extract_m3u8 "$kwik_link")
    
    if [[ -z "$stream_url" ]]; then
        echo "[ERROR] Failed to extract m3u8"
        exit 1
    fi
    
    echo "[INFO] Stream URL: $stream_url"
    
    local filename="${anime_title} - Episode ${episode}.mp4"
    
    # Download with yt-dlp (uses aria2 automatically via config)
    "$_YTDLP" "$stream_url" -o "$filename"
}

main "$@"
