import difflib
import json
import os
import re


MEDIA_PATH = "/home/unicorns/media/"
MOVIES_PATH = MEDIA_PATH + "Movies/"
TV_PATH = MEDIA_PATH + "TVShows/"


def get_movie_folders(movies_path: str = MOVIES_PATH) -> list:
    return [f for f in os.listdir(movies_path) if os.path.isdir(os.path.join(movies_path, f))]


def get_tvshow_folders(tv_path: str = TV_PATH) -> list:
    return [f for f in os.listdir(tv_path) if os.path.isdir(os.path.join(tv_path, f))]


def get_media_folders(movies_path: str = MOVIES_PATH, tv_path: str = TV_PATH) -> list:
    return [os.path.join(movies_path, f) for f in os.listdir(movies_path) if os.path.isdir(os.path.join(movies_path, f))] + [os.path.join(tv_path, f) for f in os.listdir(tv_path) if os.path.isdir(os.path.join(tv_path, f))]


def get_movie_files(movies_path: str = MOVIES_PATH, movie_folder: str = None) -> dict:
    # movie_path = os.path.join(movies_path, movie_folder)
    movie_folders = [folder for folder in os.listdir(movies_path) if os.path.isdir(os.path.join(movies_path, folder))]
    matching_folders = [folder for folder in movie_folders if movie_folder.lower() in folder.lower()]
    if matching_folders:
        movie_path = os.path.join(movies_path, matching_folders[0])
        movie_files = [file for file in os.listdir(movie_path) if os.path.isfile(os.path.join(movie_path, file))]
        movie_files = [file for file in movie_files if file.lower().endswith(('.mp4', '.avi', '.mkv', '.m2ts'))]  # Filter valid media file extensions
        if movie_files:
            return {matching_folders[0]: [os.path.join(movie_path, file) for file in movie_files]}
    return {}


# def get_tv_show_files(tv_path: str = TV_PATH, show_folder: str = None) -> dict:
#     print(f"Called get_tv_show_files with show_folder: {show_folder}")
#     folders = [folder for folder in os.listdir(tv_path) if os.path.isdir(os.path.join(tv_path, folder))]
#     matching_folders = [folder for folder in folders if show_folder.lower() in folder.lower()]
#     if not matching_folders:
#         closest_match, max_ratio = None, 0
#         for folder in folders:
#             ratio = difflib.SequenceMatcher(None, folder.lower(), show_folder.lower()).ratio()
#             if ratio > max_ratio:
#                 max_ratio = ratio
#                 closest_match = (folder, ratio)
#         if not closest_match:
#             return {}
#         # print(f"Closest match: {closest_match[0]} with ratio: {closest_match[1]}")
#         matching_folders = [closest_match[0]]
#     else:
#         # print(f"Found {len(matching_folders)} matching folders: {matching_folders}")
#         pass
#     show_dict = {}
#     for folder in matching_folders:
#         show_path = os.path.join(tv_path, folder)
#         seasons = [folder for folder in os.listdir(show_path) if os.path.isdir(os.path.join(show_path, folder))]
#         show_dict[folder] = {}
#         for season in seasons:
#             season_path = os.path.join(show_path, season)
#             episode_files = [file for file in os.listdir(season_path) if os.path.isfile(os.path.join(season_path, file))]
#             show_dict[folder][season] = {file: os.path.join(season_path, file) for file in episode_files}
#     return show_dict

def get_tv_show_files(tv_path: str = TV_PATH, show_folders: list = None) -> dict:
    if show_folders is None:
        show_folders = []
    folders = [folder for folder in os.listdir(tv_path) if os.path.isdir(os.path.join(tv_path, folder))]
    matching_folders = {folder: [] for folder in show_folders}
    for folder in folders:
        for show_folder in show_folders:
            if show_folder.lower() in folder.lower():
                matching_folders[show_folder].append(folder)
    show_dict = {}
    for show_folder, matching_folder_list in matching_folders.items():
        show_dict[show_folder] = {}
        for folder in matching_folder_list:
            show_path = os.path.join(tv_path, folder)
            seasons = [folder for folder in os.listdir(show_path) if os.path.isdir(os.path.join(show_path, folder))]
            show_dict[show_folder][folder] = {}
            for season in seasons:
                season_path = os.path.join(show_path, season)
                episode_files = [file for file in os.listdir(season_path) if os.path.isfile(os.path.join(season_path, file))]
                show_dict[show_folder][folder][season] = {file: os.path.join(season_path, file) for file in episode_files}
    return show_dict


def get_tv_show_files_extra(tv_path: str = TV_PATH, show_folder: str = None) -> dict:
    show_path = None
    for folder in os.listdir(tv_path):
        if folder.startswith(show_folder):
            show_path = os.path.join(tv_path, folder)
            break
    
    if show_path is None:
        print(f"No directory found that starts with '{show_folder}'")
        return {}
    
    seasons = [folder for folder in os.listdir(show_path) if os.path.isdir(os.path.join(show_path, folder))]
    show_dict = {show_folder: {}}
    for season in seasons:
        season_path = os.path.join(show_path, season)
        episode_files = [file for file in os.listdir(season_path) if os.path.isfile(os.path.join(season_path, file))]
        show_dict[show_folder][season] = {file: os.path.join(season_path, file) for file in episode_files}
    return show_dict

def get_tv_show_files_extra_batch(tv_path: str = TV_PATH, show_folders: list = None) -> dict:
    """
    Batch version of get_tv_show_files_extra.

    Args:
        tv_path (str): The path to the TV shows directory.
        show_folders (list): A list of show folder names.

    Returns:
        dict: A dictionary with show folder names as keys and their corresponding files as values.
    """
    if show_folders is None:
        show_folders = []
    show_dict = {}
    folders = os.listdir(tv_path)
    for show_folder in show_folders:
        show_path = next((os.path.join(tv_path, folder) for folder in folders if folder.startswith(show_folder)), None)
        if show_path is None:
            print(f"No directory found that starts with '{show_folder}'")
            continue
        seasons = [folder for folder in os.listdir(show_path) if os.path.isdir(os.path.join(show_path, folder))]
        show_dict[show_folder] = {}
        for season in seasons:
            season_path = os.path.join(show_path, season)
            episode_files = [file for file in os.listdir(season_path) if os.path.isfile(os.path.join(season_path, file))]
            show_dict[show_folder][season] = {file: os.path.join(season_path, file) for file in episode_files}
    return show_dict


from fuzzywuzzy import fuzz
def find_media_file(title: str) -> str:
    movie_folders = get_movie_folders()
    tv_folders = get_tvshow_folders()
    for folder in movie_folders:
        movie_files = get_movie_files(MOVIES_PATH, folder)
        if movie_files.get(folder):
            for file in movie_files[folder]:
                score = fuzz.partial_ratio(title.lower(), file.lower())
                if score > 80:
                    return file
    for folder in tv_folders:
        tv_files = get_tv_show_files(TV_PATH, folder)
        for season in tv_files[folder]:
            for episode in tv_files[folder][season]:
                score = fuzz.partial_ratio(title.lower(), episode.lower())
                if score > 80:
                    return tv_files[folder][season][episode]
    return ""


def is_valid_media_file(file_path: str) -> bool:
    return os.path.isfile(file_path) and file_path.lower().endswith(('.mp4', '.avi', '.mkv', '.m2ts'))


def sort_episodes(episodes):
    def extract_episode_number(file_name):
        pattern = r'S(\d+)E(\d+)'
        match = re.search(pattern, file_name)
        if match:
            return int(match.group(2))
        else:
            return float('inf')
    valid_episodes = [file_path for episode, file_path in episodes.items() if is_valid_media_file(file_path)]
    return sorted(valid_episodes, key=lambda x: extract_episode_number(os.path.basename(x)))


def sort_tv_show_episodes(tv_show_files):
    all_sorted_episodes = {}
    for show, seasons in tv_show_files.items():
        all_sorted_episodes[show] = {}
        sorted_seasons = sorted(seasons.items(), key=lambda x: int(''.join(filter(str.isdigit, x[0]))) if ''.join(filter(str.isdigit, x[0])) else 0)
        for season, episodes in sorted_seasons:
            sorted_episodes = sort_episodes(episodes)
            all_sorted_episodes[show][season] = sorted_episodes
    return all_sorted_episodes


def check_imdb_id_in_all_episodes(all_sorted_episodes, imdb_id):
    for show, seasons in all_sorted_episodes.items():
        for season, episodes in seasons.items():
            for episode in episodes:
                if imdb_id in episode:
                    return True
    return False


def get_media_type(file_path: str) -> str:
    if MOVIES_PATH in file_path:
        return "Movies"
    elif TV_PATH in file_path:
        return "TV Shows"
    else:
        return "Unknown"


def get_video_length(file_path: str) -> int:
    import cv2
    cap = cv2.VideoCapture(file_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return int(frame_count / fps)

def truncate_sorted_episodes(sorted_episodes, season):
    truncated_episodes = sorted_episodes.copy()
    for show, seasons in sorted_episodes.items():
        truncated_episodes[show] = {s: seasons[s] for s in seasons if s <= season}
    return truncated_episodes

if __name__ == '__main__':
    print("Running media_utils.py")
    video_file = "/home/unicorns/media/Mr. Robot - S01E01 - eps1.0_hellofriend.mov [Bluray-1080p] [imdbid-tt4158110] [DTS 5.1] [x264] [rovers].mkv"
    print(get_video_length(video_file))
    # tv_show_files = get_tv_show_files_extra(show_folder='Rick and Morty')
    # all_sorted_episodes = sort_tv_show_episodes(tv_show_files)
    # truncated_episodes = truncate_sorted_episodes(all_sorted_episodes, "Season 15")
    # with open("tv_show_files.json", "w") as f:
    #     json.dump(truncated_episodes, f, indent=4)
    # imdb_ids = []
    # tvshow_folders = get_tvshow_folders()
    # tv_show_files = get_tv_show_files_extra_batch(show_folders=tvshow_folders)
    # for folder in tv_show_files:
    #     files = next((season_files for season in tv_show_files.get(folder, {}) for season_files in [tv_show_files[folder][season].values()]), None)
    #     if files:
    #         path = os.path.join(TV_PATH, folder, next(iter(tv_show_files[folder])), next(iter(files)))
    #         imdb_id = re.search(r'imdbid-(tt\d+)', path)
    #         if imdb_id:
    #             imdb_id = imdb_id.group(1)
    #             imdb_ids.append(imdb_id)
    # print(imdb_ids)