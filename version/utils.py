#"""
#This file is part of Happypanda.
#Happypanda is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 2 of the License, or
#any later version.
#Happypanda is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#You should have received a copy of the GNU General Public License
#along with Happypanda.  If not, see <http://www.gnu.org/licenses/>.
#"""

import datetime
import os
import subprocess
import sys
import logging
from typing import Callable
import zipfile
import hashlib
import shutil
import uuid
import re
import rarfile
import json
import send2trash
import functools
import time
import traceback
import enum

import py7zr
from PIL import Image, ImageChops

from PyQt5.QtGui import QImage, qRgba

import app_constants
import database

log = logging.getLogger(__name__)
log_i = log.info
log_d = log.debug
log_w = log.warning
log_e = log.error
log_c = log.critical


def init_utils():
    global IMG_FILES
    global IMG_FILTER
    global ZIP_FILES
    global RAR_FILES
    global SEVENZIP_FILES
    global ARCHIVE_FILES
    global ARCHIVE_FILTER
    global SUPPORT_RAR

    IMG_FILES = ('.jpg','.bmp','.png','.gif', '.jpeg', '.webp')
    IMG_FILTER = '*.jpg *.bmp *.png *.gif *.jpeg *.webp'

    ZIP_FILES = ('.zip', '.cbz')
    RAR_FILES = ('.rar', '.cbr')
    SEVENZIP_FILES = ('.7z', 'cb7')

    ARCHIVE_FILES = ZIP_FILES + SEVENZIP_FILES

    rarfile.PATH_SEP = '/'
    rarfile.UNRAR_TOOL = app_constants.unrar_tool_path
    if app_constants.unrar_tool_path:
        if not os.path.isfile(app_constants.unrar_tool_path):
            SUPPORT_RAR = False
            log_e(f'Cannot find unrar tool: {app_constants.unrar_tool_path}')
        else:
            SUPPORT_RAR = True
            ARCHIVE_FILES += RAR_FILES

    # ('.zip', '.rar', ...) -> '*.zip *.rar ...'
    ARCHIVE_FILTER = ' '.join(f'*{ext}' for ext in ARCHIVE_FILES)


class GMetafile:
    def __init__(self, path=None, archive=''):
        self.metadata = {
            "title":'',
            "artist":'',
            "type":'',
            "tags":{},
            "language":'',
            "pub_date":'',
            "link":'',
            "info":'',
        }

        self.files = []
        if path is None: return

        if archive:
            zip = ArchiveFile(archive)
            c = zip.dir_contents(path)
            for x in c:
                if x.endswith(app_constants.GALLERY_METAFILE_KEYWORDS):
                    self.files.append(open(zip.extract(x), encoding='utf-8'))
        else:
            for p in os.scandir(path):
                if p.name in app_constants.GALLERY_METAFILE_KEYWORDS:
                    self.files.append(open(p.path, encoding='utf-8'))

        if self.files:
            self.detect()
        else:
            log_d('No metafile found...')

    def _eze(self, fp):
        if not fp.name.endswith('.json'): return

        j = json.load(fp)
        eze = ['gallery_info', 'image_api_key', 'image_info']

        # eze
        if all(x in j for x in eze):
            log_i('Detected metafile: eze')
            ezedata = j['gallery_info']
            t_parser = title_parser(ezedata['title'])
            
            self.metadata['title'] = t_parser['title']
            self.metadata['type'] = ezedata['category']
            self.metadata['language'] = ezedata['language']

            for ns in ezedata['tags']: self.metadata['tags'][ns.capitalize()] = ezedata['tags'][ns]
            self.metadata['tags']['default'] = self.metadata['tags'].pop('Misc', [])

            if 'Artist' in self.metadata['tags']:
                self.metadata['artist'] = self.metadata['tags']['Artist'][0].capitalize()
            else:
                self.metadata['artist'] = t_parser['artist']

            d = ezedata['upload_date']
            # should be zero padded
            # d[1] = int("0" + str(d[1])) if len(str(d[1])) == 1 else d[1]
            # d[3] = int("0" + str(d[1])) if len(str(d[1])) == 1 else d[1]
            self.metadata['pub_date'] = datetime.datetime.strptime(f'{d[0]} {d[1]} {d[3]}', "%Y %m %d")

            l = ezedata['source']
            self.metadata['link'] = 'http://' + l['site'] + '.org/g/' + str(l['gid']) + '/' + l['token']

            return True

    def _hdoujindler(self, fp):
        "HDoujin Downloader"
        if fp.name.endswith('info.txt'):
            log_i('Detected metafile: HDoujin text')
            lines = fp.readlines()
            if lines:
                for line in lines:
                    splitted = line.split(':', 1)
                    if len(splitted) > 1:
                        other = splitted[1].strip()
                        if not other:
                            continue
                        l = splitted[0].lower()
                        if "title" == l:
                            self.metadata['title'] = other
                        if "artist" == l:
                            self.metadata['artist'] = other.capitalize()
                        if "tags" == l:
                            self.metadata['tags'].update(tag_to_dict(other))
                        if "description" == l:
                            self.metadata['info'] = other
                        if "circle" in l:
                            if not "group" in self.metadata['tags']:
                                self.metadata['tags']['group'] = []
                                self.metadata['tags']['group'].append(other.strip().lower())
                        if "url" == l:
                            self.metadata['link'] = other
                return True

        ## Doesnt work for some reason.. too lazy to debug
        #elif fp.name.endswith('info.json'):
        #    log_i('Detected metafile: HDoujin json')
        #    j = json.load(fp)
        #    j = j['manga_info']
        #    self.metadata['title'] = j['title']
        #    for n, a in enumerate(j['artist']):
        #        at = a
        #        if not n+1 == len(j['artist']):
        #            at += ', '
        #        self.metadata['artist'] += at
        #        tags = {}
        #        for x in j['tags']:
        #            ns = 'default' if x == 'misc' else x.capitalize()
        #            tags[ns] = []
        #            for y in j[tags][x]:
        #                tags[ns].append(y.strip().lower())
        #        self.metadata['tags'] = tags
        #        self.metadata['link'] = j['url']
        #        self.metadata['info'] = j['description']
        #        for x in j['circle']:
        #            if not "group" in self.metadata['tags']:
        #                self.metadata['tags']['group'] = []
        #                self.metadata['tags']['group'].append(x.strip().lower())
        #        return True

    def detect(self):
        for fp in self.files:
            with fp:
                z = False
                for x in [self._eze, self._hdoujindler]:
                    try:
                        if x(fp):
                            z = True
                            break
                    except Exception:
                        log.exception('Error in parsing metafile')
                        continue
                if not z:
                    log_i('Incompatible metafiles found')

    def update(self, other):
        self.metadata.update((x, y) for x, y in other.metadata.items() if y)

    def apply_gallery(self, gallery):
        log_i('Applying metafile to gallery')
        if self.metadata['title']:
            gallery.title = self.metadata['title']
        if self.metadata['artist']:
            gallery.artist = self.metadata['artist']
        if self.metadata['type']:
            gallery.type = self.metadata['type']
        if self.metadata['tags']:
            gallery.tags = self.metadata['tags']
        if self.metadata['language']:
            gallery.language = self.metadata['language']
        if self.metadata['pub_date']:
            gallery.pub_date = self.metadata['pub_date']
        if self.metadata['link']:
            gallery.link = self.metadata['link']
        if self.metadata['info']:
            gallery.info = self.metadata['info']
        return gallery

def backup_database(db_path: str = None):
    if db_path is None: db_path = database.db_constants.DB_PATH

    log_i('Perfoming database backup')
    date = f'{datetime.datetime.today()}'.split(' ')[0]
    base_path, name = os.path.split(db_path)
    backup_dir = os.path.join(base_path, 'backup')
    if not os.path.isdir(backup_dir):
        os.mkdir(backup_dir)
    db_name = f'{date}-{name}'

    current_try = 0
    orig_db_name = db_name
    while current_try < 50:
        if current_try:
            db_name = f'{date}({current_try})-{orig_db_name}'
        try:
            dst_path = os.path.join(backup_dir, db_name)
            if os.path.exists(dst_path):
                raise ValueError
            shutil.copyfile(db_path, dst_path)
            break
        except ValueError:
            current_try += 1
    log_i(f'Database backup perfomed: {db_name}')
    return True

def get_date_age(date):
    """
    Take a datetime and return its "age" as a string.
    The age can be in second, minute, hour, day, month or year. Only the
    biggest unit is considered, e.g. if it's 2 days and 3 hours, "2 days" will
    be returned.
    Make sure date is not in the future, or else it won't work.
    """

    def formatn(n, s):
        '''Add "s" if it's plural'''

        if n == 1:
            return f'1 {s}'
        elif n > 1:
            return f'{n} {s}s'

    class PrettyDelta:
        def __init__(self, dt):
            now = datetime.datetime.now()

            delta = now - dt
            self.day = delta.days
            self.second = delta.seconds

            self.year, self.day = divmod(self.day, 365)
            self.month, self.day = divmod(self.day, 30)
            self.hour, self.second = divmod(self.second, 3600)
            self.minute, self.second = divmod(self.second, 60)

        def format(self):
            for period in ['year', 'month', 'day', 'hour', 'minute', 'second']:
                n = getattr(self, period)
                if n > 0.9:
                    return formatn(n, period)
            return "0 second"

    return PrettyDelta(date).format()

def all_opposite(*args):
    "Returns true if all items in iterable evaluae to false"
    for iterable in args:
        for x in iterable:
            if x:
                return False
    return True

def update_gallery_path(new_path, gallery):
    "Updates a gallery's chapters path"
    for chap in gallery.chapters:
        head, tail = os.path.split(chap.path)
        if gallery.path == chap.path:
            chap.path = new_path
        elif gallery.path == head:
            chap.path = os.path.join(new_path, tail)

    gallery.path = new_path
    return gallery

def move_files(path, dest='', only_path=False):
    """
    Move files to a new destination. If dest is not set,
    imported_galleries_def_path will be used instead.
    """
    if not dest:
        dest = app_constants.IMPORTED_GALLERY_DEF_PATH
        if not dest:
            return path
    f = os.path.split(path)[1]
    new_path = os.path.join(dest, f)
    if not only_path:
        log_i(f'Moving to: {new_path}')
    if new_path == os.path.join(*os.path.split(path)): # need to unpack to make sure we get the corrct sep
        return path
    if not os.path.exists(new_path):
        app_constants.TEMP_PATH_IGNORE.append(os.path.normcase(new_path))
        if not only_path:
            new_path = shutil.move(path, new_path)
    else:
        return path
    return new_path

def check_ignore_list(key):
    k = os.path.normcase(key)
    if os.path.isdir(key) and 'Folder' in app_constants.IGNORE_EXTS:
        return False
    _, ext = os.path.splitext(key)
    if ext in app_constants.IGNORE_EXTS:
        return False
    for path in app_constants.IGNORE_PATHS:
        p = os.path.normcase(path)
        if p in k:
            return False
    return True

def gallery_text_fixer(gallery):
    regex_str = app_constants.GALLERY_DATA_FIX_REGEX
    if regex_str:
        try:
            valid_regex = re.compile(regex_str)
        except re.error:
            return None
        if not valid_regex:
            return None

        def replace_regex(text):
            new_text = re.sub(regex_str, app_constants.GALLERY_DATA_FIX_REPLACE, text)
            return new_text

        if app_constants.GALLERY_DATA_FIX_TITLE:
            gallery.title = replace_regex(gallery.title)
        if app_constants.GALLERY_DATA_FIX_ARTIST:
            gallery.artist = replace_regex(gallery.artist)

        return gallery

def b_search(data, key):
    if key:
        lo = 0
        hi = len(data) - 1
        while hi >= lo:
            mid = lo + (hi - lo) // 2
            if data[mid] < key:
                lo = mid + 1
            elif data[mid] > key:
                hi = mid - 1
            else:
                return data[mid]
    return None

def generate_img_hash(src):
    """
    Generates sha1 hash based on the given bytes.
    Returns hex-digits
    """
    chunk = 8129
    sha1 = hashlib.sha1()
    buffer = src.read(chunk)
    log_d("Generating hash")
    while len(buffer) > 0:
        sha1.update(buffer)
        buffer = src.read(chunk)
    return sha1.hexdigest()


class ArchiveType(enum.IntEnum):
    NONE = 0
    ZIP = 1
    RAR = 2
    SEVENZIP = 3


class ArchiveFile():
    """
    Work with archive files. Raises exception if instance fails.

    namelist -> returns a list with all files in archive
    extract -> Extracts one specific file to given path
    open -> open the given file in archive, returns bytes
    close -> close archive
    """
    zip, rar, sevenzip = range(3)
    
    def __init__(self, filepath: str):

        self.type : ArchiveType = ArchiveType.NONE
        self.filepath = os.path.normcase(filepath)
        self.archive = None

        file_ext = os.path.splitext(filepath)[1].lower()
        try:
            if filepath.endswith(ARCHIVE_FILES):
                if file_ext in ZIP_FILES:
                    self.type = ArchiveType.ZIP
                    self.reopen()
                    b_f = self.archive.testzip()

                elif SUPPORT_RAR and file_ext in RAR_FILES:
                    self.type = ArchiveType.RAR
                    self.reopen()
                    b_f = self.archive.testrar()

                elif file_ext in SEVENZIP_FILES:
                    self.type = ArchiveType.SEVENZIP
                    with self.reopen():
                        b_f = self.archive.testzip()

                # test for corruption
                if b_f:
                    log_w(f'Bad file found in archive {filepath}: {b_f}')
                    self.close()
                    raise app_constants.CreateArchiveFail
            else:
                log_e('Archive: Unsupported file format')
                self.close()
                raise app_constants.CreateArchiveFail
        except:
            log.exception('Create archive: FAIL')
            self.close()
            raise app_constants.CreateArchiveFail

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()

    def namelist(self) -> list[str]:
        if self.type == ArchiveType.SEVENZIP:
            with self.reopen():
                return self.archive.namelist()

        return self.archive.namelist()

    def is_dir(self, name: str) -> bool:
        """
        Checks if the provided name in the archive is a directory or not
        """
        if not name: return False
        
        if not name in self.namelist():
            log_e(f'File {name} not found in archive')
            raise app_constants.FileNotFoundInArchive
        
        if self.type == ArchiveType.ZIP:
            return name.endswith('/')

        if self.type == ArchiveType.RAR:
            return self.archive.getinfo(name).isdir()

        if self.type == ArchiveType.SEVENZIP:
            with self.reopen():
                # py7zr returns directories without a '/' and there's no simpler way that I could find
                for f in self.archive.files:
                    if f.filename == name:
                        return f.is_directory
                return False

        return False

    def dir_list(self, only_top_level: bool = False) -> list[str]:
        """
        Returns a list of all directories found recursively. For directories not in toplevel
        a path in the archive to the diretory will be returned.
        """
        if only_top_level:
            if self.type == ArchiveType.ZIP:
                return [f for f in self.namelist() if f.endswith('/') and f.count('/') == 1]
                
            if self.type == ArchiveType.RAR:
                potential_dirs = [f for f in self.namelist() if f.count('/') == 0]
                return [f.filename for f in [self.archive.getinfo(d) for d in potential_dirs] if f.isdir()]

            if self.type == ArchiveType.SEVENZIP:
                with self.reopen():
                    return [f.filename for f in self.archive.files if (f.is_directory and '/' not in f.filename)]
        else:
            if self.type == ArchiveType.ZIP:
                return [f for f in self.namelist() if f.endswith('/')]

            if self.type == ArchiveType.RAR:
                return [f.filename for f in self.archive.infolist() if f.isdir()]

            if self.type == ArchiveType.SEVENZIP:
                with self.reopen():
                    return [f.filename for f in self.archive.files if f.is_directory]

    def dir_contents(self, dir_name: str) -> list[str]:
        """
        Returns a list of contents in the directory (files and direct subdirectories).
        An empty string will return the top-level contents.
        """
        if dir_name and not dir_name in self.namelist():
            log_e(f'Directory {dir_name} not found in archive')
            raise app_constants.FileNotFoundInArchive

        if not dir_name:
            # top-level contents
            if self.type == ArchiveType.ZIP:
                return [f for f in self.namelist() if f.count('/') == 0 or (f.count('/') == 1 and f.endswith('/'))]

            if self.type == ArchiveType.RAR:
                return [f for f in self.namelist() if f.count('/') == 0]

            if self.type == ArchiveType.SEVENZIP:
                with self.reopen():
                    return [f for f in self.namelist() if f.count('/') == 0]

        # contents of a directory
        if self.type == ArchiveType.ZIP:
            dir_con_start = [f for f in self.namelist() if f.startswith(dir_name)]
            return [f for f in dir_con_start if f.count('/') == dir_name.count('/') and \
                (f.count('/') == dir_name.count('/') and not f.endswith('/')) or \
                (f.count('/') == 1 + dir_name.count('/') and f.endswith('/'))]

        if self.type == ArchiveType.RAR:
            return [f for f in self.namelist() if f.startswith(dir_name) and f.count('/') == 1 + dir_name.count('/')]

        if self.type == ArchiveType.SEVENZIP:
            with self.reopen():
                return [f for f in self.namelist() if f.startswith(dir_name) and f.count('/') == 1 + dir_name.count('/')]

        return []

    def extract(self, file_or_dir: str, path: str = None) -> str:
        """
        Extracts one file or directory from archive to given path.
        Creates a temp_dir if path is not specified.
        Returns path to the extracted file.
        """
        if not path:
            path = os.path.join(app_constants.temp_dir, str(uuid.uuid4()))
            os.mkdir(path)

        if not file_or_dir:
            return self.extract_all(path)
    
        if self.type == ArchiveType.ZIP:
            # if it's a directory: get all members of that directory
            membs = [name for name in self.namelist() if (name.startswith(file_or_dir) and name != file_or_dir)]
            # but make sure to extract the directory itself first
            temp_p = self.archive.extract(file_or_dir, path)
            for m in membs:
                self.archive.extract(m, path)

        elif self.type == ArchiveType.RAR:
            temp_p = os.path.join(path, file_or_dir)
            self.archive.extract(file_or_dir, path)

        elif self.type == ArchiveType.SEVENZIP:
            with self.reopen():
                # if it's a directory: get all members of that directory
                membs = [name for name in self.archive.namelist() if (name.startswith(file_or_dir) and name != file_or_dir)]
                # but make sure to extract the directory itself first
                log_d(f'extract: {(path, file_or_dir) = }')
                self.archive.extract(path, [file_or_dir])
                temp_p = os.path.join(path, file_or_dir)
                if membs:
                    log_d(f'extract: {(path, membs) = }')
                    self.archive.extract(path, membs)

        return temp_p

    def extract_all(self, path: str = None, member: str = None) -> str:
        """
        Extracts all files to given path, and returns path
        If path is not specified, a temp dir will be created
        """
        if not path:
            path = os.path.join(app_constants.temp_dir, str(uuid.uuid4()))
            os.mkdir(path)

        if member and self.type != ArchiveType.SEVENZIP:
            self.archive.extractall(path, member)

        if self.type == ArchiveType.SEVENZIP:
            with self.reopen():
                self.archive.extractall(path)
        else:
            self.archive.extractall(path)

        return path

    def open(self, file_to_open, fp=False):
        """
        Open a file in the archive.
        Returns bytes as the file content or, if fp is True, returns file-like object.
        """
        if self.type == ArchiveType.SEVENZIP:
            fpath = self.extract(file_to_open)

            if fp: return open(fpath, 'rb')

            with open(fpath, 'rb') as f:
                content = f.read()
            os.remove(fpath)
            return content

        if fp:
            return self.archive.open(file_to_open)
        return self.archive.open(file_to_open).read()

    def close(self):
        try:
            if self.archive:
                self.archive.close()
                self.archive = None
        except:
            # log_e(f'Exception while closing ArchiveFile({self.filepath}):')
            # log_e(traceback.format_exc())
            pass

    def reopen(self) -> zipfile.ZipFile | rarfile.RarFile | py7zr.SevenZipFile:
        """
        Open the archive again after closing it and return the archive object.

        The return value of this can even be used in a with-statement.
        """
        if self.type == ArchiveType.ZIP:
            self.archive = zipfile.ZipFile(self.filepath)

        elif self.type == ArchiveType.RAR:
            self.archive = rarfile.RarFile(self.filepath)

        elif self.type == ArchiveType.SEVENZIP:
            # SevenZipFile deletes its 'files' attribute when it's closed
            if self.archive and hasattr(self.archive, 'files'):
                # must have come from a nested with-statement
                # return a new instance of the SevenZipFile
                return py7zr.SevenZipFile(self.filepath)
            self.archive = py7zr.SevenZipFile(self.filepath)

        return self.archive

def check_archive(archive_path):
    """
    Checks archive path for potential galleries.
    Returns a list with a path in archive to galleries
    if there is no directories
    """
    try:
        zip = ArchiveFile(archive_path)
    except app_constants.CreateArchiveFail:
        return []
    if not zip:
        return []
    galleries = []
    zip_dirs = zip.dir_list()
    def gallery_eval(d):
        con = zip.dir_contents(d)
        if con:
            gallery_probability = len(con)
            for n in con:
                if not n.lower().endswith(IMG_FILES):
                    gallery_probability -= 1
            if gallery_probability >= (len(con) * 0.8):
                return d
    if zip_dirs: # There are directories in the top folder
        # check parent
        r = gallery_eval('')
        if r:
            galleries.append('')
        for d in zip_dirs:
            r = gallery_eval(d)
            if r:
                galleries.append(r)
        zip.close()
    else: # all pages are in top folder
        if isinstance(gallery_eval(''), str):
            galleries.append('')
        zip.close()

    return galleries

def recursive_gallery_check(path):
    """
    Recursively checks a folder for any potential galleries
    Returns a list of paths for directories and a list of tuples where first
    index is path to gallery in archive and second index is path to archive.
    Like this:
    ["C:path/to/g"] and [("path/to/g/in/a", "C:path/to/a")]
    """
    gallery_dirs = []
    gallery_arch = []
    found_paths = 0
    for root, subfolders, files in os.walk(path):
        if files:
            for f in files:
                if f.endswith(ARCHIVE_FILES):
                    arch_path = os.path.join(root, f)
                    for g in check_archive(arch_path):
                        found_paths += 1
                        gallery_arch.append((g, arch_path))
                                    
            if not subfolders:
                if not files:
                    continue
                gallery_probability = len(files)
                for f in files:
                    if not f.lower().endswith(IMG_FILES):
                        gallery_probability -= 1
                if gallery_probability >= (len(files) * 0.8):
                    found_paths += 1
                    gallery_dirs.append(root)
    log_i(f'Found {found_paths} in {path}')
    return gallery_dirs, gallery_arch

def today():
    "Returns current date in a list: [dd, Mmm, yyyy]"
    _date = datetime.date.today()
    day = _date.strftime("%d")
    month = _date.strftime("%b")
    year = _date.strftime("%Y")
    return [day, month, year]

def external_viewer_checker(path):
    check_dict = app_constants.EXTERNAL_VIEWER_SUPPORT
    viewer = os.path.split(path)[1]
    for x in check_dict:
        allow = False
        for n in check_dict[x]:
            if viewer.lower() in n.lower():
                allow = True
                break
        if allow:
            return x

def open_chapter(chapterpath, archive=None):
    is_archive = True if archive else False
    if not is_archive:
        chapterpath = os.path.normpath(chapterpath)
    temp_p = archive if is_archive else chapterpath

    custom_args = app_constants.EXTERNAL_VIEWER_ARGS
    send_folder_t = '{$folder}'
    send_image_t = '{$file}'

    send_folder = True

    if app_constants.USE_EXTERNAL_VIEWER:
        send_folder = True

    if custom_args:
        if send_folder_t in custom_args:
            send_folder = True
        elif send_image_t in custom_args:
            send_folder = False

    def find_f_img_folder():
        if send_folder:
            return temp_p
        root, _, files = next(os.walk(temp_p))
        for f in files:
            if f.startswith('.'):
                continue
            if f.lower().endswith(IMG_FILES):
                return os.path.join(root, f)
        raise IndexError

    def find_f_img_archive(extract=True):
        with ArchiveFile(temp_p) as arch:
            if extract:
                app_constants.NOTIF_BAR.add_text('Extracting...')
                t_p = os.path.join('temp', str(uuid.uuid4()))
                os.mkdir(t_p)
                if is_archive or chapterpath.endswith(ARCHIVE_FILES):
                    if os.path.isdir(chapterpath):
                        t_p = chapterpath
                    elif chapterpath.endswith(ARCHIVE_FILES):
                        with ArchiveFile(chapterpath) as arch2:
                            f_d = sorted(arch2.dir_list(True))
                            if f_d:
                                f_d = f_d[0]
                                t_p = arch2.extract(f_d, t_p)
                            else:
                                t_p = arch2.extract('', t_p)
                    else:
                        t_p = arch.extract(chapterpath, t_p)
                else:
                    arch.extract_all(t_p) # Compatibility reasons..  TODO: REMOVE IN BETA
                if send_folder:
                    filepath = t_p
                else:
                    filepath = os.path.join(t_p, [x for x in sorted([y.name for y in os.scandir(t_p)])\
                        if x.lower().endswith(IMG_FILES) and not x.startswith('.')][0]) # Find first page
                    filepath = os.path.abspath(filepath)
            else:
                if is_archive or chapterpath.endswith(ARCHIVE_FILES):
                    con = arch.dir_contents('')
                    f_img = [x for x in sorted(con) if x.lower().endswith(IMG_FILES) and not x.startswith('.')]
                    if not f_img:
                        log_w(f'Extracting archive.. There are no images in the top-folder. ({archive})')
                        return find_f_img_archive()
                    filepath = os.path.normpath(archive)
                else:
                    app_constants.NOTIF_BAR.add_text("Fatal error: Unsupported gallery!")
                    raise ValueError("Unsupported gallery version")
            return filepath

    try:
        if os.path.isdir(temp_p):
            filepath = find_f_img_folder()
        else:
            try:
                if not app_constants.EXTRACT_CHAPTER_BEFORE_OPENING and app_constants.EXTERNAL_VIEWER_PATH:
                    filepath = find_f_img_archive(False)
                else:
                    filepath = find_f_img_archive()
            except app_constants.CreateArchiveFail:
                log.exception('Could not open chapter')
                app_constants.NOTIF_BAR.add_text('Could not open chapter. Check happypanda.log for more details.')
                return
    except FileNotFoundError:
        log.exception(f'Could not find chapter {chapterpath}')
        app_constants.NOTIF_BAR.add_text("Chapter no longer exists!")
        return
    except IndexError:
        log.exception(f'No images found: {chapterpath}')
        app_constants.NOTIF_BAR.add_text("No images found in chapter!")
        return

    if send_folder_t in custom_args:
        custom_args = custom_args.replace(send_folder_t, filepath)
    elif send_image_t in custom_args:
        custom_args = custom_args.replace(send_image_t, filepath)
    else:
        custom_args = filepath

    try:
        app_constants.NOTIF_BAR.add_text('Opening chapter...')
        if not app_constants.USE_EXTERNAL_VIEWER:
            if sys.platform.startswith('darwin'):
                subprocess.Popen(('open', custom_args))
            elif os.name == 'nt':
                os.startfile(custom_args)
            elif os.name == 'posix':
                subprocess.Popen(('xdg-open', custom_args))
        else:
            ext_path = app_constants.EXTERNAL_VIEWER_PATH
            viewer = external_viewer_checker(ext_path)
            if viewer == 'honeyview':
                if app_constants.OPEN_GALLERIES_SEQUENTIALLY:
                    subprocess.run((ext_path, custom_args))
                else:
                    subprocess.Popen((ext_path, custom_args))
            else:
                if app_constants.OPEN_GALLERIES_SEQUENTIALLY:
                    subprocess.run((ext_path, custom_args), check=True)
                else:
                    subprocess.Popen((ext_path, custom_args))
    except subprocess.CalledProcessError:
        app_constants.NOTIF_BAR.add_text("Could not open chapter. Invalid external viewer.")
        log.exception('Could not open chapter. Invalid external viewer.')
    except:
        app_constants.NOTIF_BAR.add_text("Could not open chapter for unknown reasons. Check happypanda.log!")
        log_e(f'Could not open chapter {os.path.split(chapterpath)[1]}')

def get_gallery_img(gallery_or_path, chap_number=0):
    """
    Returns a path to image in gallery chapter
    """
    archive = None
    if isinstance(gallery_or_path, str):
        path = gallery_or_path
    else:
        path = gallery_or_path.chapters[chap_number].path
        if gallery_or_path.is_archive:
            archive = gallery_or_path.path

    # TODO: add chapter support
    try:
        name = os.path.split(path)[1]
    except IndexError:
        name = os.path.split(path)[0]
    is_archive = True if archive or name.endswith(ARCHIVE_FILES) else False
    real_path = archive if archive else path
    img_path = None
    if is_archive:
        try:
            log_i('Getting image from archive')
            arc = ArchiveFile(real_path)
            log_d(f'{arc = }')
            temp_path = os.path.join(app_constants.temp_dir, str(uuid.uuid4()))
            os.mkdir(temp_path)
            log_d(f'{temp_path = }')
            if not archive:
                f_img_name = sorted([img for img in arc.namelist() if img.lower().endswith(IMG_FILES) and not img.startswith('.')])[0]
            else:
                f_img_name = sorted([img for img in arc.dir_contents(path) if img.lower().endswith(IMG_FILES) and not img.startswith('.')])[0]
            log_d(f'{f_img_name = }')
            img_path = arc.extract(f_img_name, temp_path)
            log_d(f'{img_path = }')
            arc.close()
        except app_constants.CreateArchiveFail:
            img_path = app_constants.NO_IMAGE_PATH
    elif os.path.isdir(real_path):
        log_i('Getting image from folder')
        first_img = sorted([img.name for img in os.scandir(real_path) if img.name.lower().endswith(tuple(IMG_FILES)) and not img.name.startswith('.')])
        if first_img:
            img_path = os.path.join(real_path, first_img[0])

    if img_path:
        return os.path.abspath(img_path)
    else:
        log_e("Could not get gallery image")

def tag_to_string(gallery_tag, simple=False):
    """
    Takes gallery tags and converts it to string, returns string
    if simple is set to True, returns a CSV string, else a dict-like string
    """
    assert isinstance(gallery_tag, dict), "Please provide a dict like this: {'namespace':['tag1']}"
    string = ""
    if not simple:
        for n, namespace in enumerate(sorted(gallery_tag), 1):
            if len(gallery_tag[namespace]) != 0:
                if namespace != 'default':
                    string += namespace + ":"

                # find tags
                if namespace != 'default' and len(gallery_tag[namespace]) > 1:
                    string += '['
                for x, tag in enumerate(sorted(gallery_tag[namespace]), 1):
                    # if we are at the end of the list
                    if x == len(gallery_tag[namespace]):
                        string += tag
                    else:
                        string += tag + ', '
                if namespace != 'default' and len(gallery_tag[namespace]) > 1:
                    string += ']'

                # if we aren't at the end of the list
                if not n == len(gallery_tag):
                    string += ', '
    else:
        for n, namespace in enumerate(sorted(gallery_tag), 1):
            if len(gallery_tag[namespace]) != 0:
                if namespace != 'default':
                    string += namespace + ","

                # find tags
                for x, tag in enumerate(sorted(gallery_tag[namespace]), 1):
                    # if we are at the end of the list
                    if x == len(gallery_tag[namespace]):
                        string += tag
                    else:
                        string += tag + ', '

                # if we aren't at the end of the list
                if not n == len(gallery_tag):
                    string += ', '

    return string

def tag_to_dict(string, ns_capitalize=True):
    "Receives a string of tags and converts it to a dict of tags"
    namespace_tags = {'default':[]}
    level = 0 # so we know if we are in a list
    buffer = ""
    stripped_set = set() # we only need unique values
    for n, x in enumerate(string, 1):

        if x == '[':
            level += 1 # we are now entering a list
        if x == ']':
            level -= 1 # we are now exiting a list


        if x == ',': # if we meet a comma
            # we trim our buffer if we are at top level
            if level == 0:
                # add to list
                stripped_set.add(buffer.strip())
                buffer = ""
            else:
                buffer += x
        elif n == len(string): # or at end of string
            buffer += x
            # add to list
            stripped_set.add(buffer.strip())
            buffer = ""
        else:
            buffer += x

    def tags_in_list(br_tags):
        "Receives a string of tags enclosed in brackets, returns a list with tags"
        unique_tags = set()
        tags = br_tags.replace('[', '').replace(']','')
        tags = tags.split(',')
        for t in tags:
            if len(t) != 0:
                unique_tags.add(t.strip().lower())
        return list(unique_tags)

    unique_tags = set()
    for ns_tag in stripped_set:
        splitted_tag = ns_tag.split(':')
        # if there is a namespace
        if len(splitted_tag) > 1 and len(splitted_tag[0]) != 0:
            if splitted_tag[0] != 'default':
                if ns_capitalize:
                    namespace = splitted_tag[0].capitalize()
                else:
                    namespace = splitted_tag[0]
            else:
                namespace = splitted_tag[0]
            tags = splitted_tag[1]
            # if tags are enclosed in brackets
            if '[' in tags and ']' in tags:
                tags = tags_in_list(tags)
                tags = [x for x in tags if len(x) != 0]
                # if namespace is already in our list
                if namespace in namespace_tags:
                    for t in tags:
                        # if tag not already in ns list
                        if not t in namespace_tags[namespace]:
                            namespace_tags[namespace].append(t)
                else:
                    # to avoid empty strings
                    namespace_tags[namespace] = tags
            else: # only one tag
                if len(tags) != 0:
                    if namespace in namespace_tags:
                        namespace_tags[namespace].append(tags)
                    else:
                        namespace_tags[namespace] = [tags]
        else: # no namespace specified
            tag = splitted_tag[0]
            if len(tag) != 0:
                unique_tags.add(tag.lower())

    if len(unique_tags) != 0:
        for t in unique_tags:
            namespace_tags['default'].append(t)

    return namespace_tags

def title_parser(title):
    "Receives a title to parse. Returns dict with 'title', 'artist' and language"
    log_d(f'Parsing title: {title}')

    #If title is not absolute, then it's not a pathname and we allow a "/" inside it
    if (os.path.isabs(title)): title = os.path.basename(title)

    title = " ".join(title.split())

    for x in ARCHIVE_FILES:
        if title.endswith(x):
            title = title[:-len(x)]

    parsed_title = {'title':"", 'artist':"", 'language':""}
    try:
        a = re.findall(r'((?<=\[) *[^\]]+( +\S+)* *(?=\]))', title)
        assert len(a) != 0
        try:
            artist = a[0][0].strip()
        except IndexError:
            artist = ''
        parsed_title['artist'] = artist

        try:
            assert a[1]
            lang = app_constants.G_LANGUAGES + app_constants.G_CUSTOM_LANGUAGES
            for x in a:
                l = x[0].strip()
                l = l.lower()
                l = l.capitalize()
                if l in lang:
                    parsed_title['language'] = l
                    break
            else:
                parsed_title['language'] = app_constants.G_DEF_LANGUAGE
        except IndexError:
            parsed_title['language'] = app_constants.G_DEF_LANGUAGE

        t = title
        for x in a:
            t = t.replace(x[0], '')

        t = t.replace('[]', '')

        # remove things like (C86), (COMIC1☆10), etc. from beginning of title
        if app_constants.GALLERY_TRIM_PARENTHESES:
            nt = re.sub(r'^(\([^\)]+\) *)+', '', t)
            if len(nt) > 0: t = nt
        
        # remove anything in curly braces like {5 a.m.}, {Hennojin}, etc.
        if app_constants.GALLERY_TRIM_CURLY:
            nt = re.sub(r'{[^}]+}', '', t)
            if len(nt) > 0: t = nt

        # some galleries have titles like '(C92) romaji title | translated title (franchise)'
        if app_constants.GALLERY_TITLE_SEP != 'both':
            if '｜' in t or '|' in t:
                # The inclusion of parentheses in the regex before the separator makes the regex engine run into an infinite loop for titles like
                #   [Nagashiro Rouge] When Magical Girls Kiss Chapter 1-3 (END) | Eigyou Mahou Shoujo ga Kiss Shitara Chapter 1-3 (END)
                # But taking them out will make it think that parentheses that were kept at the start of the title like the (Bokura no Love Live! 41) here
                #   (Bokura no Love Live! 41) [Kitaku Jikan (Kitaku)] Oshiri 100% | 100% Butt (Love Live! Nijigasaki High School Idol Club) [English]
                # are part of the left variant of the title. But unless I implement another way to parse the title parts, I think losing that bit is preferable to the application freezing.
                # 
                # This entire function should probably completely separate the title into its components and reassemble it from only the parts the user cares about.
                # But that's a total pain because uploaders can't seem to stick to even a handful of standards for gallery titles.

                # p = re.search(r'(([^|｜\(\)\[\]]+\s*)+)\s*[|｜]\s*(([^|｜\(\)\[\]]+\s*)+)', t)
                p = re.search(r'(([^|｜]+\s*)+)\s*[|｜]\s*(([^|｜]+\s*)+)', t)
                if app_constants.GALLERY_TITLE_SEP == 'left':
                    t = ' '.join([t[:p.span()[0]], p[1], t[p.span()[1]:]])
                elif app_constants.GALLERY_TITLE_SEP == 'right':
                    t = ' '.join([t[:p.span()[0]], p[3], t[p.span()[1]:]])

        # replace multi-spaces with singles
        nt = re.sub(r' +', ' ', t).strip()
        if len(nt) > 0: t = nt

        parsed_title['title'] = t
        
    except AssertionError:
        parsed_title['title'] = title

    return parsed_title

import webbrowser
def open_web_link(url):
    if not url:
        return
    try:
        webbrowser.open_new_tab(url)
    except:
        log_e('Could not open URL in browser')

def open_path(path, select=''):
    ""
    try:
        if sys.platform.startswith('darwin'):
            subprocess.Popen(['open', path])
        elif os.name == 'nt':
            if select:
                subprocess.Popen(f'explorer.exe /select,"{os.path.normcase(select)}"', shell=True)
            else:
                os.startfile(path)
        elif os.name == 'posix':
            subprocess.Popen(('xdg-open', path))
        else:
            app_constants.NOTIF_BAR.add_text("I don't know how you've managed to do this.. If you see this, you're in deep trouble...")
            log_e('Could not open path: no OS found')
    except:
        app_constants.NOTIF_BAR.add_text("Could not open specified location. It might not exist anymore.")
        log_e('Could not open path')

def open_torrent(path):
    if not app_constants.TORRENT_CLIENT:
        open_path(path)
    else:
        subprocess.Popen([app_constants.TORRENT_CLIENT, path])

def delete_path(path):
    "Deletes the provided recursively"
    s = True
    if os.path.exists(path):
        error = ''
        if app_constants.SEND_FILES_TO_TRASH:
            try:
                send2trash.send2trash(path)
            except:
                log.exception("Unable to send file to trash")
                error = 'Unable to send file to trash'
        else:
            try:
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)
            except PermissionError:
                error = 'PermissionError'
            except FileNotFoundError:
                pass

        if error:
            p = os.path.split(path)[1]
            log_e(f'Failed to delete: {error}:{p}')
            app_constants.NOTIF_BAR.add_text(f'An error occured while trying to delete: {error}')
            s = False
    return s

def regex_search(a, b, override_case=False, args=[]):
    "Looks for a in b"
    if a and b:
        try:
            if not app_constants.Search.Case in args or override_case:
                if re.search(a, b, re.IGNORECASE):
                    return True
            else:
                if re.search(a, b):
                    return True
        except re.error:
            pass
    return False

def search_term(a, b, override_case=False, args=[]):
    "Searches for a in b"
    if a and b:
        if not app_constants.Search.Case in args or override_case:
            b = b.lower()
            a = a.lower()

        if app_constants.Search.Strict in args:
            if a == b:
                return True
        else:
            if a in b:
                return True
    return False

def get_terms(term):
    "Dividies term into pieces. Returns a list with the pieces"

    # some variables we will use
    pieces = []
    piece = ''
    qoute_level = 0
    bracket_level = 0
    brackets_tags = {}
    current_bracket_ns = ''
    end_of_bracket = False
    blacklist = ['[', ']', '"', ',']

    for n, x in enumerate(term):
        # if we meet brackets
        if x == '[':
            bracket_level += 1
            brackets_tags[piece] = set() # we want unique tags!
            current_bracket_ns = piece
        elif x == ']':
            bracket_level -= 1
            end_of_bracket = True

        # if we meet a double qoute
        if x == '"':
            if qoute_level > 0:
                qoute_level -= 1
            else:
                qoute_level += 1

        # if we meet a whitespace, comma or end of term and are not in a double qoute
        if (x == ' ' or x == ',' or n == len(term) - 1) and qoute_level == 0:
            # if end of term and x is allowed
            if (n == len(term) - 1) and not x in blacklist and x != ' ':
                piece += x
            if piece:
                if bracket_level > 0 or end_of_bracket: # if we are inside a bracket we put piece in the set
                    end_of_bracket = False
                    if piece.startswith(current_bracket_ns):
                        piece = piece[len(current_bracket_ns):]
                    if piece:
                        try:
                            brackets_tags[current_bracket_ns].add(piece)
                        except KeyError: # keyerror when there is a closing bracket without a starting bracket
                            pass
                else:
                    pieces.append(piece) # else put it in the normal list
            piece = ''
            continue

        # else append to the buffers
        if not x in blacklist:
            if qoute_level > 0: # we want to include everything if in double qoute
                piece += x
            elif x != ' ':
                piece += x

    # now for the bracket tags
    for ns in brackets_tags:
        for tag in brackets_tags[ns]:
            ns_tag = ns
            # if they want to exlucde this tag
            if tag[0] == '-':
                if ns_tag[0] != '-':
                    ns_tag = '-' + ns
                tag = tag[1:] # remove the '-'

            # put them together
            ns_tag += tag

            # done
            pieces.append(ns_tag)

    return pieces

def image_greyscale(filepath):
    """
    Check if image is monochrome (1 channel or 3 identical channels)
    """
    log_d(f'Checking if img is monochrome: {filepath}')
    im = Image.open(filepath).convert("RGB")
    if im.mode not in ("L", "RGB"):
        return False

    if im.mode == "RGB":
        rgb = im.split()
        if ImageChops.difference(rgb[0],rgb[1]).getextrema()[1] != 0: 
            return False
        if ImageChops.difference(rgb[0],rgb[2]).getextrema()[1] != 0: 
            return False
    return True

def PToQImageHelper(im):
    """
    The Python Imaging Library (PIL) is

    Copyright © 1997-2011 by Secret Labs AB
    Copyright © 1995-2011 by Fredrik Lundh
    """
    def rgb(r, g, b, a=255):
        """(Internal) Turns an RGB color into a Qt compatible color integer."""
        # use qRgb to pack the colors, and then turn the resulting long
        # into a negative integer with the same bitpattern.
        return (qRgba(r, g, b, a) & 0xffffffff)

    def align8to32(bytes, width, mode):
        """
        converts each scanline of data from 8 bit to 32 bit aligned
        """

        bits_per_pixel = {
            '1': 1,
            'L': 8,
            'P': 8,
        }[mode]

        # calculate bytes per line and the extra padding if needed
        bits_per_line = bits_per_pixel * width
        full_bytes_per_line, remaining_bits_per_line = divmod(bits_per_line, 8)
        bytes_per_line = full_bytes_per_line + (1 if remaining_bits_per_line else 0)

        extra_padding = -bytes_per_line % 4

        # already 32 bit aligned by luck
        if not extra_padding:
            return bytes

        new_data = []
        for i in range(len(bytes) // bytes_per_line):
            new_data.append(bytes[i*bytes_per_line:(i+1)*bytes_per_line] + b'\x00' * extra_padding)

        return b''.join(new_data)

    data = None
    colortable = None

    # handle filename, if given instead of image name
    if hasattr(im, "toUtf8"):
        # FIXME - is this really the best way to do this?
        if str is bytes:
            im = unicode(im.toUtf8(), "utf-8")
        else:
            im = str(im.toUtf8(), "utf-8")
    if isinstance(im, (bytes, str)):
        im = Image.open(im)

    if im.mode == "1":
        format = QImage.Format_Mono
    elif im.mode == "L":
        format = QImage.Format_Indexed8
        colortable = []
        for i in range(256):
            colortable.append(rgb(i, i, i))
    elif im.mode == "P":
        format = QImage.Format_Indexed8
        colortable = []
        palette = im.getpalette()
        for i in range(0, len(palette), 3):
            colortable.append(rgb(*palette[i:i+3]))
    elif im.mode == "RGB":
        data = im.tobytes("raw", "BGRX")
        format = QImage.Format_RGB32
    elif im.mode == "RGBA":
        try:
            data = im.tobytes("raw", "BGRA")
        except SystemError:
            # workaround for earlier versions
            r, g, b, a = im.split()
            im = Image.merge("RGBA", (b, g, r, a))
        format = QImage.Format_ARGB32
    else:
        raise ValueError("unsupported image mode %r" % im.mode)

    # must keep a reference, or Qt will crash!
    __data = data or align8to32(im.tobytes(), im.size[0], im.mode)
    return {
        'data': __data, 'im': im, 'format': format, 'colortable': colortable
    }

def make_chapters(gallery_object):
    chap_container = gallery_object.chapters
    path = gallery_object.path
    metafile = GMetafile()
    if os.path.isdir(path):
        log_d('Listing dir...')
        con = os.scandir(path) # list all folders in gallery dir
        log_i('Gallery source is a directory')
        log_d('Sorting')
        chapters = sorted([sub.path for sub in con if sub.is_dir() or sub.name.endswith(ARCHIVE_FILES)]) #subfolders
        # if gallery has chapters divided into sub folders
        if len(chapters) != 0:
            log_d('Chapters divided in folders..')
            for ch in chapters:
                chap = chap_container.create_chapter()
                chap.title = title_parser(ch)['title']
                chap.path = os.path.join(path, ch)
                metafile.update(GMetafile(chap.path))
                chap.pages = len([x for x in os.scandir(chap.path) if x.name.lower().endswith(IMG_FILES)])

        else: #else assume that all images are in gallery folder
            chap = chap_container.create_chapter()
            chap.title = title_parser(os.path.split(path)[1])['title']
            chap.path = path
            metafile.update(GMetafile(path))
            chap.pages = len([x for x in os.scandir(path) if x.name.lower().endswith(IMG_FILES)])

    else:
        if path.endswith(ARCHIVE_FILES):
            gallery_object.is_archive = 1
            log_i("Gallery source is an archive")
            archive_g = sorted(check_archive(path))
            for g in archive_g:
                chap = chap_container.create_chapter()
                chap.path = g
                chap.in_archive = 1
                metafile.update(GMetafile(g, path))
                arch = ArchiveFile(path)
                chap.pages = len(arch.dir_contents(g))
                arch.close()

    metafile.apply_gallery(gallery_object)

def timeit(func):
    @functools.wraps(func)
    def newfunc(*args, **kwargs):
        startTime = time.time()
        func(*args, **kwargs)
        elapsedTime = time.time() - startTime
        print(f'function [{func.__name__}] finished in {int(elapsedTime * 1000)} ms')
    return newfunc


def makedirs_if_not_exists(folder):
    """Create directory if not exists.
    Args:
        folder: Target folder.
    """
    if not os.path.isdir(folder):
        os.makedirs(folder)

def lookup_tag(tag):
    "Issues a tag lookup on preferred site"
    assert isinstance(tag, str), "str not " + str(type(tag))
    # remove whitespace at edges and replace whitespace with +
    tag = tag.strip().lower().replace(' ', '+')
    url = app_constants.DEFAULT_EHEN_URL
    if not url.endswith('/'):
        url += '/'

    if not ':' in tag:
        tag = 'misc:' + tag

    url += 'tag/' + tag

    open_web_link(url)


class Stopwatch(object):
    def __init__(self, name: str, out_func: Callable, ns: bool = False):
        super(Stopwatch, self).__init__()
        self.name      : str      = name
        self._start    : float    = None
        self._out_func : Callable = out_func
        self._ns       : bool     = ns
        self._unit = 'ns' if ns else 's'

    def __enter__(self):
        self._start = time.perf_counter_ns() if self._ns else time.perf_counter()

    def __exit__(self, *args, **kwargs):
        end = time.perf_counter_ns() if self._ns else time.perf_counter()
        self._out_func(f'{self.name}: {round(end - self._start, 6)}{self._unit}')