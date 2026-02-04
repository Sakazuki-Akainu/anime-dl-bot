#!/usr/bin/env bash
# KOYEB ADAPTED VERSION

set -e
set -u

# 🟢 HELPER: Use Python Scraper instead of Curl
get() {
    python3 scraper.py "$1"
}

set_var() {
    _JQ="jq"
    if [[ -z ${ANIMEPAHE_DL_NODE:-} ]]; then
        _NODE="node"
    else
        _NODE="$ANIMEPAHE_DL_NODE"
    fi
    _FFMPEG="ffmpeg"
    _OPENSSL="openssl"

    _HOST="https://animepahe.si"
    _ANIME_URL="$_HOST/anime"
    _API_URL="$_HOST/api"
    _REFERER_URL="https://kwik.cx/"

    _SCRIPT_PATH=$(dirname "$(realpath "$0")")
    _ANIME_LIST_FILE="$_SCRIPT_PATH/anime.list"
    _SOURCE_FILE=".source.json"
}

set_args() {
    _PARALLEL_JOBS=1
    while getopts ":hlda:s:e:r:t:o:" opt; do
        case $opt in
            a) _INPUT_ANIME_NAME="$OPTARG" ;;
            s) _ANIME_SLUG="$OPTARG" ;;
            e) _ANIME_EPISODE="$OPTARG" ;;
            l) _LIST_LINK_ONLY=true ;;
            r) _ANIME_RESOLUTION="$OPTARG" ;;
            t) _PARALLEL_JOBS="$OPTARG" ;;
            o) _ANIME_AUDIO="$OPTARG" ;;
            d) _DEBUG_MODE=true; set -x ;;
            h) echo "Usage info..." && exit 0 ;;
            \?) echo "Invalid option" && exit 1 ;;
        esac
    done
}

print_info() { echo "[INFO] $1"; }
print_warn() { echo "[WARNING] $1"; }
print_error() { echo "[ERROR] $1"; exit 1; }

download_anime_list() {
    get "$_ANIME_URL" | grep "/anime/" | sed -E 's/.*anime\//[/;s/" title="/] /;s/\">.*/   /;s/" title/]/' > "$_ANIME_LIST_FILE"
}

search_anime_by_name() {
    local d
    d="$(get "$_HOST/api?m=search&q=${1// /%20}")"
    local n
    n=$(echo "$d" | "$_JQ" -r '.total')
    
    if [[ "$n" == "0" || -z "$n" ]]; then
        echo ""
    else
        # 🟢 CHANGED: Automatically pick the first result (No interactive FZF)
        echo "$d" | "$_JQ" -r '.data[0] | "[\(.session)] \(.title)   "' | awk -F'] ' '{print $2}'
    fi
}

get_episode_list() {
    get "${_API_URL}?m=release&id=${1}&sort=episode_asc&page=${2}"
}

download_source() {
    local d p n
    mkdir -p "$_SCRIPT_PATH/$_ANIME_NAME"
    d="$(get_episode_list "$_ANIME_SLUG" "1")"
    p=$(echo "$d" | "$_JQ" -r '.last_page')

    if [[ "$p" != "null" && "$p" -gt "1" ]]; then
        for i in $(seq 2 "$p"); do
            n="$(get_episode_list "$_ANIME_SLUG" "$i")"
            d="$(echo "$d $n" | "$_JQ" -s '.[0].data + .[1].data | {data: .}')"
        done
    fi
    echo "$d" > "$_SCRIPT_PATH/$_ANIME_NAME/$_SOURCE_FILE"
}

get_episode_link() {
    local s o l r=""
    s=$("$_JQ" -r '.data[] | select((.episode | tonumber) == ($num | tonumber)) | .session' --arg num "$1" < "$_SCRIPT_PATH/$_ANIME_NAME/$_SOURCE_FILE")
    [[ "$s" == "" ]] && print_warn "Episode $1 not found!" && return
    
    o="$(get "${_HOST}/play/${_ANIME_SLUG}/${s}")"
    
    l="$(echo "$o" | grep \<button | grep data-src | sed -E 's/data-src="/\n/g' | grep 'data-av1="0"')"

    if [[ -n "${_ANIME_RESOLUTION:-}" ]]; then
        r="$(grep 'data-resolution="'"$_ANIME_RESOLUTION"'"' <<< "${r:-$l}")"
    fi

    if [[ -z "${r:-}" ]]; then
        # Fallback to whatever is available if resolution not matches
        grep kwik <<< "$l" | tail -1 | grep kwik | awk -F '"' '{print $1}'
    else
        awk -F '" ' '{print $1}' <<< "$r" | tail -1
    fi
}

get_playlist_link() {
    local s l
    # Use python scraper to bypass cloudflare on Kwik
    s="$(get "$1")"
    
    # Extract JS
    local js_extract
    js_extract=$(echo "$s" | grep "<script>eval(" | awk -F 'script>' '{print $2}'| sed -E 's/document/process/g' | sed -E 's/querySelector/exit/g' | sed -E 's/eval\(/console.log\(/g')
    
    # Run Node to decode
    l="$("$_NODE" -e "$js_extract" | grep 'source=' | sed -E "s/.m3u8';.*/.m3u8/" | sed -E "s/.*const source='//")"
    echo "$l"
}

download_episode() {
    local num="$1" l pl v
    v="$_SCRIPT_PATH/${_ANIME_NAME}/${_ANIME_NAME} - Episode ${num}.mp4"
    
    l=$(get_episode_link "$num")
    [[ "$l" != *"/"* ]] && print_warn "Link error!" && return
    
    pl=$(get_playlist_link "$l")
    [[ -z "${pl:-}" ]] && print_warn "Playlist error!" && return

    print_info "Downloading Episode $1..."
    
    # Use FFmpeg to download the m3u8 stream
    "$_FFMPEG" -headers "Referer: $_REFERER_URL" -i "$pl" -c copy -y "$v"
}

download_episodes() {
    local e="$1"
    download_episode "$e"
}

remove_slug() { awk -F'] ' '{print $2}'; }
get_slug_from_name() { grep "] $1" "$_ANIME_LIST_FILE" | tail -1 | awk -F']' '{print $1}' | sed -E 's/^\[//'; }

main() {
    set_args "$@"
    set_var
    
    # 🟢 Auto-Search (Non-Interactive)
    if [[ -n "${_INPUT_ANIME_NAME:-}" ]]; then
        print_info "Searching for: $_INPUT_ANIME_NAME"
        search_res=$(search_anime_by_name "$_INPUT_ANIME_NAME")
        
        if [[ -z "$search_res" ]]; then
            print_error "Anime not found"
        fi
        
        # Manually extract Slug from the first result found
        _ANIME_NAME="$search_res"
        # We need to re-download list to find slug if searching
        download_anime_list
        _ANIME_SLUG="$(get_slug_from_name "$_ANIME_NAME")"
    fi

    if [[ -z "$_ANIME_SLUG" ]]; then
        print_error "Slug not found!"
    fi
    
    _ANIME_NAME_CLEAN="${_ANIME_NAME//[^a-zA-Z0-9]/_}"
    _ANIME_NAME="$_ANIME_NAME_CLEAN"
    
    download_source
    download_episodes "$_ANIME_EPISODE"
}

main "$@"
