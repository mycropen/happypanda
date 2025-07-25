﻿import logging, os, sys

from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QListWidget, QWidget,
                             QListWidgetItem, QStackedLayout, QPushButton,
                             QLabel, QTabWidget, QLineEdit, QGroupBox, QFormLayout,
                             QCheckBox, QRadioButton, QSpinBox, QSizePolicy,
                             QScrollArea, QFontDialog, QMessageBox, QComboBox,
                             QFileDialog, QSlider)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QPalette, QPixmapCache

from color_line_edit import ColorLineEdit
from misc import FlowLayout, Spacer, PathLineEdit, AppDialog, Line
import misc
import settings
import app_constants
import misc_db
import gallerydb
import utils
import io_misc
import pewnet

log = logging.getLogger(__name__)
log_i = log.info
log_d = log.debug
log_w = log.warning
log_e = log.error
log_c = log.critical

class SettingsDialog(QWidget):
    "A settings dialog"
    scroll_speed_changed = pyqtSignal()
    init_gallery_rebuild = pyqtSignal(bool)
    init_gallery_eximport = pyqtSignal(object)
    def __init__(self, parent=None):
        super().__init__(parent, flags=Qt.Window)

        self.init_gallery_rebuild.connect(self.accept)

        self.parent_widget = parent
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.resize(800, 650)
        self.restore_values()
        self.initUI()
        self.setWindowTitle('Settings')
        self.show()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        sub_layout = QHBoxLayout()
        # Left Panel
        left_panel = QListWidget()
        left_panel.setViewMode(left_panel.ListMode)
        #left_panel.setIconSize(QSize(40,40))
        left_panel.setTextElideMode(Qt.ElideRight)
        left_panel.setMaximumWidth(200)
        left_panel.itemClicked.connect(self.change)
        #web.setText('Web')
        self.application = QListWidgetItem()
        self.application.setText('Application')
        self.web = QListWidgetItem()
        self.web.setText('Web')
        self.visual = QListWidgetItem()
        self.visual.setText('Visual')
        self.advanced = QListWidgetItem()
        self.advanced.setText('Advanced')
        self.about = QListWidgetItem()
        self.about.setText('About')

        #main.setIcon(QIcon(os.path.join(app_constants.static_dir, 'plus2.png')))
        left_panel.addItem(self.application)
        left_panel.addItem(self.web)
        left_panel.addItem(self.visual)
        left_panel.addItem(self.advanced)
        left_panel.addItem(self.about)
        left_panel.setMaximumWidth(100)

        # right panel
        self.right_panel = QStackedLayout()
        self.init_right_panel()

        # bottom
        bottom_layout = QHBoxLayout()
        ok_btn = QPushButton('Ok')
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton('Cancel')
        cancel_btn.clicked.connect(self.close)
        info_lbl = QLabel()
        info_lbl.setText('<a href="https://github.com/mycropen/happypanda">Visit GitHub Repo</a> | Options marked with * requires application restart.')
        info_lbl.setTextFormat(Qt.RichText)
        info_lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
        info_lbl.setOpenExternalLinks(True)
        self.spacer = QWidget()
        self.spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        bottom_layout.addWidget(info_lbl, 0, Qt.AlignLeft)
        bottom_layout.addWidget(self.spacer)
        bottom_layout.addWidget(ok_btn, 0, Qt.AlignRight)
        bottom_layout.addWidget(cancel_btn, 0, Qt.AlignRight)

        sub_layout.addWidget(left_panel)
        sub_layout.addLayout(self.right_panel)
        main_layout.addLayout(sub_layout)
        main_layout.addLayout(bottom_layout)

        self.restore_options()

    def change(self, item):
        def curr_index(index):
            if index != self.right_panel.currentIndex():
                self.right_panel.setCurrentIndex(index)
        if item == self.application:
            curr_index(self.application_index)
        elif item == self.web:
            curr_index(self.web_index)
        elif item == self.visual:
            curr_index(self.visual_index)
        elif item == self.advanced:
            curr_index(self.advanced_index)
        elif item == self.about:
            curr_index(self.about_index)

    def restore_values(self):
        # Visual
        self.high_quality_thumbs = app_constants.HIGH_QUALITY_THUMBS
        self.style_sheet = app_constants.user_stylesheet_path

        # Advanced
        self.scroll_speed = app_constants.SCROLL_SPEED
        self.cache_size = app_constants.THUMBNAIL_CACHE_SIZE
        self.prefetch_item_amnt = app_constants.PREFETCH_ITEM_AMOUNT

    def restore_options(self):

        # App / General
        self.g_languages.addItems(app_constants.G_LANGUAGES)
        self.g_languages.addItems(app_constants.G_CUSTOM_LANGUAGES)
        self._find_combobox_match(self.g_languages, app_constants.G_DEF_LANGUAGE, 0)
        self.g_type.addItems(app_constants.G_TYPES)
        self._find_combobox_match(self.g_type, app_constants.G_DEF_TYPE, 0)
        self.g_status.addItems(app_constants.G_STATUS)
        self._find_combobox_match(self.g_status, app_constants.G_DEF_STATUS, 0)
        self.sidebar_widget_hidden.setChecked(app_constants.SHOW_SIDEBAR_WIDGET)
        self.send_2_trash.setChecked(app_constants.SEND_FILES_TO_TRASH)
        self.subfolder_as_chapters.setChecked(app_constants.SUBFOLDER_AS_GALLERY)
        self.extract_gallery_before_opening.setChecked(app_constants.EXTRACT_CHAPTER_BEFORE_OPENING)
        self.open_galleries_sequentially.setChecked(app_constants.OPEN_GALLERIES_SEQUENTIALLY)
        self.move_imported_gs.setChecked(app_constants.MOVE_IMPORTED_GALLERIES)
        self.move_imported_def_path.setText(app_constants.IMPORTED_GALLERY_DEF_PATH)
        self.open_random_g_chapters.setChecked(app_constants.OPEN_RANDOM_GALLERY_CHAPTERS)
        self.rename_g_source_group.setChecked(app_constants.RENAME_GALLERY_SOURCE)
        self.path_to_unrar.setText(app_constants.unrar_tool_path)
        self.keep_added_gallery.setChecked(not app_constants.KEEP_ADDED_GALLERIES)
        self.enable_notifications.setChecked(app_constants.ENABLE_NOTIFICATIONS)
        self.always_drop_to_inbox.setChecked(app_constants.ALWAYS_DROP_TO_INBOX)

        # App / Gallery / New Gallery Fixes
        self.new_gallery_trim_starting_paren_checkbox.setChecked(app_constants.GALLERY_TRIM_PARENTHESES)
        self.new_gallery_trim_curly.setChecked(app_constants.GALLERY_TRIM_CURLY)
        keep_side = app_constants.GALLERY_TITLE_SEP
        if keep_side in app_constants.G_TITLE_SIDES:
            self.new_gallery_keep_title.setCurrentIndex(app_constants.G_TITLE_SIDES.index(keep_side))

        # App / General / External Viewer
        self.external_viewer_path.setText(app_constants.EXTERNAL_VIEWER_PATH)

        # App / Monitoring / Misc
        self.enable_monitor.setChecked(app_constants.ENABLE_MONITOR)
        self.look_new_gallery_startup.setChecked(app_constants.LOOK_NEW_GALLERY_STARTUP)

        # App / Monitoring / Folders
        for path in app_constants.MONITOR_PATHS:
            self.add_folder_monitor(path)

        # App / Monitoring / Ignore list
        for ext in app_constants.IGNORE_EXTS:
            if ext == 'Folder':
                self.ignore_folder.setChecked(True)
            if ext == 'ZIP':
                self.ignore_zip.setChecked(True)
            if ext == 'CBZ':
                self.ignore_cbz.setChecked(True)
            if ext == 'RAR':
                self.ignore_rar.setChecked(True)
            if ext == 'CBR':
                self.ignore_cbr.setChecked(True)

        for path in app_constants.IGNORE_PATHS:
            self.add_ignore_path(path)

        # Web / metadata
        if 'e-hentai' in app_constants.DEFAULT_EHEN_URL:
            self.default_ehen_url.setChecked(True)
        else:
            self.exhentai_ehen_url.setChecked(True)
        
        self.include_expunged.setChecked(app_constants.INCLUDE_EH_EXPUNGED)
        self.replace_metadata.setChecked(app_constants.REPLACE_METADATA)
        self.always_first_hit.setChecked(app_constants.ALWAYS_CHOOSE_FIRST_HIT)
        self.web_time_offset.setValue(app_constants.GLOBAL_EHEN_TIME)
        self.continue_a_metadata_fetcher.setChecked(app_constants.CONTINUE_AUTO_METADATA_FETCHER)
        self.use_jpn_title.setChecked(app_constants.USE_JPN_TITLE)
        self.always_apply_title.setCurrentIndex(app_constants.ALWAYS_APPLY_TITLE)
        self.always_apply_artist.setCurrentIndex(app_constants.ALWAYS_APPLY_ARTIST)
        self.always_apply_language.setCurrentIndex(app_constants.ALWAYS_APPLY_LANGUAGE)
        self.always_apply_g_type.setCurrentIndex(app_constants.ALWAYS_APPLY_G_TYPE)
        self.always_apply_tags.setCurrentIndex(app_constants.ALWAYS_APPLY_TAGS)
        self.use_gallery_link.setChecked(app_constants.USE_GALLERY_LINK)
        self.use_global_ehen_lock.setChecked(app_constants.USE_GLOBAL_EHEN_LOCK)
        self.fallback_chaika.setChecked(True) if 'chaikahen' in app_constants.HEN_LIST else None

        # Web / Download
        if app_constants.HEN_DOWNLOAD_TYPE == 0:
            self.archive_download.setChecked(True)
        else:
            self.torrent_download.setChecked(True)

        self.download_directory.setText(app_constants.DOWNLOAD_DIRECTORY)
        self.torrent_client.setText(app_constants.TORRENT_CLIENT)
        self.download_gallery_lib.setChecked(app_constants.DOWNLOAD_GALLERY_TO_LIB)

        # Visual / General
        self.galleryedit_width.setValue(app_constants.GALLERY_EDIT_WIDTH)

        # Visual / Grid View
        self.g_popup_width.setValue(app_constants.POPUP_WIDTH)
        self.g_popup_height.setValue(app_constants.POPUP_HEIGHT)
        # Visual / Grid View / Tooltip
        self.grid_tooltip_group.setChecked(app_constants.GRID_TOOLTIP)
        self.visual_grid_tooltip_title.setChecked(app_constants.TOOLTIP_TITLE)
        self.visual_grid_tooltip_author.setChecked(app_constants.TOOLTIP_AUTHOR)
        self.visual_grid_tooltip_chapters.setChecked(app_constants.TOOLTIP_CHAPTERS)
        self.visual_grid_tooltip_status.setChecked(app_constants.TOOLTIP_STATUS)
        self.visual_grid_tooltip_type.setChecked(app_constants.TOOLTIP_TYPE)
        self.visual_grid_tooltip_lang.setChecked(app_constants.TOOLTIP_LANG)
        self.visual_grid_tooltip_descr.setChecked(app_constants.TOOLTIP_DESCR)
        self.visual_grid_tooltip_tags.setChecked(app_constants.TOOLTIP_TAGS)
        self.visual_grid_tooltip_last_read.setChecked(app_constants.TOOLTIP_LAST_READ)
        self.visual_grid_tooltip_times_read.setChecked(app_constants.TOOLTIP_TIMES_READ)
        self.visual_grid_tooltip_pub_date.setChecked(app_constants.TOOLTIP_PUB_DATE)
        self.visual_grid_tooltip_date_added.setChecked(app_constants.TOOLTIP_DATE_ADDED)
        # Visual / Grid View / Gallery
        self.gallery_rating.setChecked(app_constants.DISPLAY_RATING)
        self.gallery_type_ico.setChecked(app_constants.DISPLAY_GALLERY_TYPE)
        if app_constants.GALLERY_FONT_ELIDE:
            self.gallery_text_elide.setChecked(True)
        else:
            self.gallery_text_fit.setChecked(True)
        self.font_lbl.setText(app_constants.GALLERY_FONT[0])
        self.font_size_lbl.setValue(app_constants.GALLERY_FONT[1])

        if app_constants.SEARCH_ON_ENTER:
            self.search_on_enter.setChecked(True)
        else:
            self.search_every_keystroke.setChecked(True)
        self.gallery_size.setValue(app_constants.SIZE_FACTOR//10)
        self.grid_spacing.setValue(app_constants.GRID_SPACING)
        # Visual / Grid View / Colors
        self.grid_label_color.setText(app_constants.GRID_VIEW_LABEL_COLOR)
        self.grid_title_color.setText(app_constants.GRID_VIEW_TITLE_COLOR)
        self.grid_artist_color.setText(app_constants.GRID_VIEW_ARTIST_COLOR)

        self.colors_ribbon_group.setChecked(app_constants.DISPLAY_GALLERY_RIBBON)
        self.ribbon_manga_color.setText(app_constants.GRID_VIEW_T_MANGA_COLOR)
        self.ribbon_doujin_color.setText(app_constants.GRID_VIEW_T_DOUJIN_COLOR)
        self.ribbon_artist_cg_color.setText(app_constants.GRID_VIEW_T_ARTIST_CG_COLOR)
        self.ribbon_game_cg_color.setText(app_constants.GRID_VIEW_T_GAME_CG_COLOR)
        self.ribbon_western_color.setText(app_constants.GRID_VIEW_T_WESTERN_COLOR)
        self.ribbon_image_color.setText(app_constants.GRID_VIEW_T_IMAGE_COLOR)
        self.ribbon_non_h_color.setText(app_constants.GRID_VIEW_T_NON_H_COLOR)
        self.ribbon_cosplay_color.setText(app_constants.GRID_VIEW_T_COSPLAY_COLOR)
        self.ribbon_other_color.setText(app_constants.GRID_VIEW_T_OTHER_COLOR)

        # Advanced / Misc
        self.external_viewer_args.setText(app_constants.EXTERNAL_VIEWER_ARGS)
        self.force_high_dpi_support.setChecked(app_constants.FORCE_HIGH_DPI_SUPPORT)

        # Advanced / Gallery / Gallery Text Fixer
        self.g_data_regex_fix_edit.setText(app_constants.GALLERY_DATA_FIX_REGEX)
        self.g_data_replace_fix_edit.setText(app_constants.GALLERY_DATA_FIX_REPLACE)
        self.g_data_fixer_title.setChecked(app_constants.GALLERY_DATA_FIX_TITLE)
        self.g_data_fixer_artist.setChecked(app_constants.GALLERY_DATA_FIX_ARTIST)

    def accept(self):
        set = settings.set

        # App / General
        app_constants.SHOW_SIDEBAR_WIDGET = self.sidebar_widget_hidden.isChecked()
        set(app_constants.SHOW_SIDEBAR_WIDGET, 'Application', 'show sidebar widget')
        app_constants.SEND_FILES_TO_TRASH = self.send_2_trash.isChecked()
        set(app_constants.SEND_FILES_TO_TRASH, 'Application', 'send files to trash')
        app_constants.ENABLE_NOTIFICATIONS = self.enable_notifications.isChecked()
        set(app_constants.ENABLE_NOTIFICATIONS, 'Application', 'enable notifications')
        app_constants.ALWAYS_DROP_TO_INBOX = self.always_drop_to_inbox.isChecked()
        set(app_constants.ALWAYS_DROP_TO_INBOX, 'Application', 'always send to inbox')

        # App / General / Gallery

        app_constants.KEEP_ADDED_GALLERIES = not self.keep_added_gallery.isChecked()
        set(app_constants.KEEP_ADDED_GALLERIES, 'Application', 'keep added galleries')

        g_custom_lang = []
        for x in range(self.g_languages.count()):
            l = self.g_languages.itemText(x).capitalize()
            if l and not l in app_constants.G_LANGUAGES:
                g_custom_lang.append(l)

        app_constants.G_CUSTOM_LANGUAGES = g_custom_lang
        set(app_constants.G_CUSTOM_LANGUAGES, 'General', 'gallery custom languages')
        if self.g_languages.currentText():
            app_constants.G_DEF_LANGUAGE = self.g_languages.currentText()
            set(app_constants.G_DEF_LANGUAGE, 'General', 'gallery default language')
        app_constants.G_DEF_STATUS = self.g_status.currentText()
        set(app_constants.G_DEF_STATUS, 'General', 'gallery default status')
        app_constants.G_DEF_TYPE = self.g_type.currentText()
        set(app_constants.G_DEF_TYPE, 'General', 'gallery default type')
        app_constants.SUBFOLDER_AS_GALLERY = self.subfolder_as_chapters.isChecked()
        set(app_constants.SUBFOLDER_AS_GALLERY, 'Application', 'subfolder as gallery')
        app_constants.EXTRACT_CHAPTER_BEFORE_OPENING = self.extract_gallery_before_opening.isChecked()
        set(app_constants.EXTRACT_CHAPTER_BEFORE_OPENING, 'Application', 'extract chapter before opening')
        app_constants.OPEN_GALLERIES_SEQUENTIALLY = self.open_galleries_sequentially.isChecked()
        set(app_constants.OPEN_GALLERIES_SEQUENTIALLY, 'Application', 'open galleries sequentially')
        app_constants.MOVE_IMPORTED_GALLERIES = self.move_imported_gs.isChecked()
        set(app_constants.MOVE_IMPORTED_GALLERIES, 'Application', 'move imported galleries')
        if not self.move_imported_def_path.text() or os.path.exists(self.move_imported_def_path.text()):
            app_constants.IMPORTED_GALLERY_DEF_PATH = self.move_imported_def_path.text()
            set(app_constants.IMPORTED_GALLERY_DEF_PATH, 'Application', 'imported gallery def path')
        app_constants.OPEN_RANDOM_GALLERY_CHAPTERS = self.open_random_g_chapters.isChecked()
        set(app_constants.OPEN_RANDOM_GALLERY_CHAPTERS, 'Application', 'open random gallery chapters')
        app_constants.RENAME_GALLERY_SOURCE = self.rename_g_source_group.isChecked()
        set(app_constants.RENAME_GALLERY_SOURCE, 'Application', 'rename gallery source')
        app_constants.unrar_tool_path = self.path_to_unrar.text()
        set(app_constants.unrar_tool_path, 'Application', 'unrar tool path')
        # App / General / Search
        app_constants.SEARCH_AUTOCOMPLETE = self.search_autocomplete.isChecked()
        set(app_constants.SEARCH_AUTOCOMPLETE, 'Application', 'search autocomplete')
        app_constants.DUAL_SEARCH = self.dual_search.isChecked()
        set(app_constants.DUAL_SEARCH, 'Application', 'dual gallery search')
        app_constants.SEARCHABLE_INBOX = self.searchable_inbox.isChecked()
        set(app_constants.SEARCHABLE_INBOX, 'Application', 'searchable inbox')
        app_constants.SEARCH_ON_ENTER = self.search_on_enter.isChecked()
        set(app_constants.SEARCH_ON_ENTER, 'Application', 'search on enter')
        # App / General / External Viewer
        if not self.external_viewer_path.text():
            app_constants.USE_EXTERNAL_VIEWER = False
            set(False, 'Application', 'use external viewer')
        else:
            app_constants.USE_EXTERNAL_VIEWER = True
            set(True, 'Application', 'use external viewer')
            app_constants._REFRESH_EXTERNAL_VIEWER = True
        app_constants.EXTERNAL_VIEWER_PATH = self.external_viewer_path.text()
        set(app_constants.EXTERNAL_VIEWER_PATH, 'Application', 'external viewer path')
        # App / Gallery / New Gallery Fixes
        app_constants.GALLERY_TRIM_PARENTHESES = self.new_gallery_trim_starting_paren_checkbox.isChecked()
        set(app_constants.GALLERY_TRIM_PARENTHESES, 'Application', 'trim starting parentheses')
        app_constants.GALLERY_TRIM_CURLY = self.new_gallery_trim_curly.isChecked()
        set(app_constants.GALLERY_TRIM_CURLY, 'Application', 'remove curly braces')
        app_constants.GALLERY_TITLE_SEP = app_constants.G_TITLE_SIDES[self.new_gallery_keep_title.currentIndex()]
        set(app_constants.GALLERY_TITLE_SEP, 'Application', 'keep side of title with vertical bar')
        # App / Monitoring / misc
        app_constants.ENABLE_MONITOR = self.enable_monitor.isChecked()
        set(app_constants.ENABLE_MONITOR, 'Application', 'enable monitor')
        app_constants.LOOK_NEW_GALLERY_STARTUP = self.look_new_gallery_startup.isChecked()
        set(app_constants.LOOK_NEW_GALLERY_STARTUP, 'Application', 'look new gallery startup')
        # App / Monitoring / folders
        paths = []
        folder_p_widgets = self.take_all_layout_widgets(self.folders_layout)
        for x, l_edit in enumerate(folder_p_widgets):
            p = l_edit.text()
            if p:
                paths.append(p)

        set(paths, 'Application', 'monitor paths')
        app_constants.MONITOR_PATHS = paths
        # App / Monitoring / ignore list
        exts_list = []
        for ext in [self.ignore_folder, self.ignore_zip, self.ignore_cbz, self.ignore_rar, self.ignore_cbr]:
            if ext.isChecked():
                exts_list.append(ext.text())
        set(exts_list, 'Application', 'ignore exts')
        app_constants.IGNORE_EXTS = exts_list

        paths = []
        ignore_p_widgets = self.take_all_layout_widgets(self.ignore_path_l)
        for x, l_edit in enumerate(ignore_p_widgets):
            p = l_edit.text()
            if p:
                paths.append(p)
        set(paths, 'Application', 'ignore paths')
        app_constants.IGNORE_PATHS = paths

        # Web / Downloader

        if self.archive_download.isChecked():
            app_constants.HEN_DOWNLOAD_TYPE = 0
        else:
            app_constants.HEN_DOWNLOAD_TYPE = 1
        set(app_constants.HEN_DOWNLOAD_TYPE, 'Web', 'hen download type')

        app_constants.DOWNLOAD_DIRECTORY = self.download_directory.text()
        set(app_constants.DOWNLOAD_DIRECTORY, 'Web', 'download directory')

        app_constants.TORRENT_CLIENT = self.torrent_client.text()
        set(app_constants.TORRENT_CLIENT, 'Web', 'torrent client')

        app_constants.DOWNLOAD_GALLERY_TO_LIB = self.download_gallery_lib.isChecked()
        set(app_constants.DOWNLOAD_GALLERY_TO_LIB, 'Web', 'download galleries to library')

        # Web / Metdata
        if self.default_ehen_url.isChecked():
            app_constants.DEFAULT_EHEN_URL = 'https://e-hentai.org/'
        else:
            app_constants.DEFAULT_EHEN_URL = 'https://exhentai.org/'
        set(app_constants.DEFAULT_EHEN_URL, 'Web', 'default ehen url')

        app_constants.INCLUDE_EH_EXPUNGED = self.include_expunged.isChecked()
        set(app_constants.INCLUDE_EH_EXPUNGED, 'Web', 'include eh expunged')

        app_constants.REPLACE_METADATA = self.replace_metadata.isChecked()
        set(app_constants.REPLACE_METADATA, 'Web', 'replace metadata')

        app_constants.ALWAYS_CHOOSE_FIRST_HIT = self.always_first_hit.isChecked()
        set(app_constants.ALWAYS_CHOOSE_FIRST_HIT, 'Web', 'always choose first hit')

        app_constants.GLOBAL_EHEN_TIME = self.web_time_offset.value()
        set(app_constants.GLOBAL_EHEN_TIME, 'Web', 'global ehen time offset')

        app_constants.CONTINUE_AUTO_METADATA_FETCHER = self.continue_a_metadata_fetcher.isChecked()
        set(app_constants.CONTINUE_AUTO_METADATA_FETCHER, 'Web', 'continue auto metadata fetcher')

        app_constants.USE_JPN_TITLE = self.use_jpn_title.isChecked()
        set(app_constants.USE_JPN_TITLE, 'Web', 'use jpn title')

        app_constants.ALWAYS_APPLY_TITLE = self.always_apply_title.currentIndex()
        set(app_constants.ALWAYS_APPLY_TITLE, 'Web', 'always apply title')

        app_constants.ALWAYS_APPLY_ARTIST = self.always_apply_artist.currentIndex()
        set(app_constants.ALWAYS_APPLY_ARTIST, 'Web', 'always apply artist')

        app_constants.ALWAYS_APPLY_LANGUAGE = self.always_apply_language.currentIndex()
        set(app_constants.ALWAYS_APPLY_LANGUAGE, 'Web', 'always apply language')

        app_constants.ALWAYS_APPLY_G_TYPE = self.always_apply_g_type.currentIndex()
        set(app_constants.ALWAYS_APPLY_G_TYPE, 'Web', 'always apply gallery type')

        app_constants.ALWAYS_APPLY_TAGS = self.always_apply_tags.currentIndex()
        set(app_constants.ALWAYS_APPLY_TAGS, 'Web', 'always apply tags')

        app_constants.USE_GALLERY_LINK = self.use_gallery_link.isChecked()
        set(app_constants.USE_GALLERY_LINK, 'Web', 'use gallery link')

        app_constants.USE_GLOBAL_EHEN_LOCK = self.use_global_ehen_lock.isChecked()
        set(app_constants.USE_GLOBAL_EHEN_LOCK, 'Web', 'global ehen metadata fetch lock')
        # fallback sources
        henlist = []
        if self.fallback_chaika.isChecked():
            henlist.append('chaikahen')
        app_constants.HEN_LIST = henlist
        set(app_constants.HEN_LIST, 'Web', 'hen list')

        # Visual / General
        app_constants.GALLERY_EDIT_WIDTH = self.galleryedit_width.value()
        set(app_constants.GALLERY_EDIT_WIDTH, 'Visual', 'galleryedit.w')

        # Visual / Grid View
        app_constants.POPUP_WIDTH = self.g_popup_width.value()
        set(app_constants.POPUP_WIDTH, 'Visual', 'popup.w')
        app_constants.POPUP_HEIGHT = self.g_popup_height.value()
        set(app_constants.POPUP_HEIGHT, 'Visual', 'popup.h')

        # Visual / Grid View / Tooltip
        app_constants.GRID_TOOLTIP = self.grid_tooltip_group.isChecked()
        set(app_constants.GRID_TOOLTIP, 'Visual', 'grid tooltip')
        app_constants.TOOLTIP_TITLE = self.visual_grid_tooltip_title.isChecked()
        set(app_constants.TOOLTIP_TITLE, 'Visual', 'tooltip title')
        app_constants.TOOLTIP_AUTHOR = self.visual_grid_tooltip_author.isChecked()
        set(app_constants.TOOLTIP_AUTHOR, 'Visual', 'tooltip author')
        app_constants.TOOLTIP_CHAPTERS = self.visual_grid_tooltip_chapters.isChecked()
        set(app_constants.TOOLTIP_CHAPTERS, 'Visual', 'tooltip chapters')
        app_constants.TOOLTIP_STATUS = self.visual_grid_tooltip_status.isChecked()
        set(app_constants.TOOLTIP_STATUS, 'Visual', 'tooltip status')
        app_constants.TOOLTIP_TYPE = self.visual_grid_tooltip_type.isChecked()
        set(app_constants.TOOLTIP_TYPE, 'Visual', 'tooltip type')
        app_constants.TOOLTIP_LANG = self.visual_grid_tooltip_lang.isChecked()
        set(app_constants.TOOLTIP_LANG, 'Visual', 'tooltip lang')
        app_constants.TOOLTIP_DESCR = self.visual_grid_tooltip_descr.isChecked()
        set(app_constants.TOOLTIP_DESCR, 'Visual', 'tooltip descr')
        app_constants.TOOLTIP_TAGS = self.visual_grid_tooltip_tags.isChecked()
        set(app_constants.TOOLTIP_TAGS, 'Visual', 'tooltip tags')
        app_constants.TOOLTIP_LAST_READ = self.visual_grid_tooltip_last_read.isChecked()
        set(app_constants.TOOLTIP_LAST_READ, 'Visual', 'tooltip last read')
        app_constants.TOOLTIP_TIMES_READ = self.visual_grid_tooltip_times_read.isChecked()
        set(app_constants.TOOLTIP_TIMES_READ, 'Visual', 'tooltip times read')
        app_constants.TOOLTIP_PUB_DATE = self.visual_grid_tooltip_pub_date.isChecked()
        set(app_constants.TOOLTIP_PUB_DATE, 'Visual', 'tooltip pub date')
        app_constants.TOOLTIP_DATE_ADDED = self.visual_grid_tooltip_date_added.isChecked()
        set(app_constants.TOOLTIP_DATE_ADDED, 'Visual', 'tooltip date added')
        # Visual / Grid View / Gallery
        app_constants.DISPLAY_RATING = self.gallery_rating.isChecked()
        set(app_constants.DISPLAY_RATING, 'Visual', 'display gallery rating')
        app_constants.DISPLAY_GALLERY_TYPE = self.gallery_type_ico.isChecked()
        set(app_constants.DISPLAY_GALLERY_TYPE, 'Visual', 'display gallery type')
        if self.gallery_text_elide.isChecked():
            app_constants.GALLERY_FONT_ELIDE = True
        else:
            app_constants.GALLERY_FONT_ELIDE = False
        set(app_constants.GALLERY_FONT_ELIDE, 'Visual', 'gallery font elide')
        app_constants.GALLERY_FONT = (self.font_lbl.text(), self.font_size_lbl.value())
        set(app_constants.GALLERY_FONT[0], 'Visual', 'gallery font family')
        set(app_constants.GALLERY_FONT[1], 'Visual', 'gallery font size')
        app_constants.SIZE_FACTOR = self.gallery_size.value() * 10
        set(app_constants.SIZE_FACTOR, 'Visual', 'size factor')
        app_constants.GRID_SPACING = self.grid_spacing.value()
        set(app_constants.GRID_SPACING, 'Visual', 'grid spacing')

        # Visual / Grid View / Colors
        app_constants.DISPLAY_GALLERY_RIBBON = self.colors_ribbon_group.isChecked()
        set(app_constants.DISPLAY_GALLERY_RIBBON, 'Visual', 'display gallery ribbon')
        if self.color_checker(self.grid_title_color.text()):
            app_constants.GRID_VIEW_TITLE_COLOR = self.grid_title_color.text()
            set(app_constants.GRID_VIEW_TITLE_COLOR, 'Visual', 'grid view title color')
        if self.color_checker(self.grid_artist_color.text()):
            app_constants.GRID_VIEW_ARTIST_COLOR = self.grid_artist_color.text()
            set(app_constants.GRID_VIEW_ARTIST_COLOR, 'Visual', 'grid view artist color')
        if self.color_checker(self.grid_label_color.text()):
            app_constants.GRID_VIEW_LABEL_COLOR = self.grid_label_color.text()
            set(app_constants.GRID_VIEW_LABEL_COLOR, 'Visual', 'grid view label color')

        if self.color_checker(self.ribbon_manga_color.text()):
            app_constants.GRID_VIEW_T_MANGA_COLOR = self.ribbon_manga_color.text()
            set(app_constants.GRID_VIEW_T_MANGA_COLOR, 'Visual', 'grid view t manga color')
        if self.color_checker(self.ribbon_doujin_color.text()):
            app_constants.GRID_VIEW_T_DOUJIN_COLOR = self.ribbon_doujin_color.text()
            set(app_constants.GRID_VIEW_T_DOUJIN_COLOR, 'Visual', 'grid view t doujin color')
        if self.color_checker(self.ribbon_artist_cg_color.text()):
            app_constants.GRID_VIEW_T_ARTIST_CG_COLOR = self.ribbon_artist_cg_color.text()
            set(app_constants.GRID_VIEW_T_ARTIST_CG_COLOR, 'Visual', 'grid view t artist cg color')
        if self.color_checker(self.ribbon_game_cg_color.text()):
            app_constants.GRID_VIEW_T_GAME_CG_COLOR = self.ribbon_game_cg_color.text()
            set(app_constants.GRID_VIEW_T_GAME_CG_COLOR, 'Visual', 'grid view t game cg color')
        if self.color_checker(self.ribbon_western_color.text()):
            app_constants.GRID_VIEW_T_WESTERN_COLOR = self.ribbon_western_color.text()
            set(app_constants.GRID_VIEW_T_WESTERN_COLOR, 'Visual', 'grid view t western color')
        if self.color_checker(self.ribbon_image_color.text()):
            app_constants.GRID_VIEW_T_IMAGE_COLOR = self.ribbon_image_color.text()
            set(app_constants.GRID_VIEW_T_IMAGE_COLOR, 'Visual', 'grid view t image color')
        if self.color_checker(self.ribbon_non_h_color.text()):
            app_constants.GRID_VIEW_T_NON_H_COLOR = self.ribbon_non_h_color.text()
            set(app_constants.GRID_VIEW_T_NON_H_COLOR, 'Visual', 'grid view t non-h color')
        if self.color_checker(self.ribbon_cosplay_color.text()):
            app_constants.GRID_VIEW_T_COSPLAY_COLOR = self.ribbon_cosplay_color.text()
            set(app_constants.GRID_VIEW_T_COSPLAY_COLOR, 'Visual', 'grid view t cosplay color')
        if self.color_checker(self.ribbon_other_color.text()):
            app_constants.GRID_VIEW_T_OTHER_COLOR = self.ribbon_other_color.text()
            set(app_constants.GRID_VIEW_T_OTHER_COLOR, 'Visual', 'grid view t other color')


        # Advanced / Misc
        app_constants.EXTERNAL_VIEWER_ARGS = self.external_viewer_args.text()
        set(app_constants.EXTERNAL_VIEWER_ARGS, 'Advanced', 'external viewer args')

        # Advanced / Misc / Grid View
        app_constants.SCROLL_SPEED = self.scroll_speed
        set(self.scroll_speed, 'Advanced', 'scroll speed')
        self.scroll_speed_changed.emit()
        app_constants.THUMBNAIL_CACHE_SIZE = self.cache_size
        set(self.cache_size[1], 'Advanced', 'cache size')
        QPixmapCache.setCacheLimit(self.cache_size[0]*
                             self.cache_size[1])

        app_constants.FORCE_HIGH_DPI_SUPPORT = self.force_high_dpi_support.isChecked()
        set(app_constants.FORCE_HIGH_DPI_SUPPORT, 'Advanced', 'force high dpi support')

        # Advanced / General / Gallery Text Fixer
        app_constants.GALLERY_DATA_FIX_REGEX = self.g_data_regex_fix_edit.text()
        set(app_constants.GALLERY_DATA_FIX_REGEX, 'Advanced', 'gallery data fix regex')
        app_constants.GALLERY_DATA_FIX_TITLE = self.g_data_fixer_title.isChecked()
        set(app_constants.GALLERY_DATA_FIX_TITLE, 'Advanced', 'gallery data fix title')
        app_constants.GALLERY_DATA_FIX_ARTIST = self.g_data_fixer_artist.isChecked()
        set(app_constants.GALLERY_DATA_FIX_ARTIST, 'Advanced', 'gallery data fix artist')
        app_constants.GALLERY_DATA_FIX_REPLACE = self.g_data_replace_fix_edit.text()
        set(app_constants.GALLERY_DATA_FIX_REPLACE, 'Advanced', 'gallery data fix replace')

        # Advanced / Database
        app_constants.DATABASE_STARTUP_FETCH_LIMIT = self.advanced_dbstartup_fetch_limit_spinbox.value()
        set(app_constants.DATABASE_STARTUP_FETCH_LIMIT, 'Application', 'db startup fetch limit')

        # About / DB Overview

        settings.save()
        self.close()

    def init_right_panel(self):

        def groupbox(name, layout, parent, add_groupbox_in_layout=None):
            """
            Makes a groupbox and a layout for you
            Returns groupbox and layout
            """
            g = QGroupBox(name, parent)
            l = layout(g)
            if add_groupbox_in_layout:
                if isinstance(add_groupbox_in_layout, QFormLayout):
                    add_groupbox_in_layout.addRow(g)
                else:
                    add_groupbox_in_layout.addWidget(g)
            return g, l

        def option_lbl_checkbox(text, optiontext, parent=None):
            l = QLabel(text)
            c = QCheckBox(text, parent)
            return l, c

        def new_tab(name, parent, scroll=False):
            """
            Creates a new tab.
            Returns new tab page widget and it's layout
            """
            new_t = QWidget(parent)
            new_l = QFormLayout(new_t)
            if scroll:
                scr = QScrollArea(parent)
                scr.setBackgroundRole(QPalette.Base)
                scr.setWidget(new_t)
                scr.setWidgetResizable(True)
                parent.addTab(scr, name)
                return new_t, new_l
            else:
                parent.addTab(new_t, name)
            return new_t, new_l

        # App
        application = QTabWidget(self)
        self.application_index = self.right_panel.addWidget(application)


        # App / General
        application_general, app_general_m_l = new_tab('General', application, True)
        self.sidebar_widget_hidden = QCheckBox("Show sidebar widget on startup")

        self.send_2_trash = QCheckBox("Send deleted files to recycle bin", self)
        app_general_m_l.addRow(self.sidebar_widget_hidden)
        self.send_2_trash.setToolTip("When unchecked, files will get deleted permanently and be unrecoverable!")
        app_general_m_l.addRow(self.send_2_trash)
        self.keep_added_gallery = QCheckBox("Remove galleries added in inbox on exit")
        self.keep_added_gallery.setToolTip("When turned off, galleries in inbox will not be deleted on exit")
        app_general_m_l.addRow(self.keep_added_gallery)
        self.enable_notifications = QCheckBox("Enable desktop notifications", self)
        app_general_m_l.addRow(self.enable_notifications)
        self.always_drop_to_inbox = QCheckBox("Send every new gallery to the Inbox", self)
        self.always_drop_to_inbox.setToolTip("If unchecked, then dragging a single gallery onto Happypanda will open an edit dialog instead.")
        app_general_m_l.addRow(self.always_drop_to_inbox)


        # App / General / Search
        app_search, app_search_layout = groupbox('Search', QFormLayout, application_general)
        app_general_m_l.addRow(app_search)

        self.search_autocomplete = QCheckBox('*')
        self.search_autocomplete.setChecked(app_constants.SEARCH_AUTOCOMPLETE)
        self.search_autocomplete.setToolTip('Turn autocomplete on/off')
        app_search_layout.addRow('Autocomplete', self.search_autocomplete)
        self.dual_search = QCheckBox('*')
        self.dual_search.setChecked(app_constants.DUAL_SEARCH)
        self.dual_search.setToolTip('Search both Library and Inbox at the same time')
        app_search_layout.addRow('Dual search', self.dual_search)
        self.searchable_inbox = QCheckBox('*')
        self.searchable_inbox.setChecked(app_constants.SEARCHABLE_INBOX)
        self.searchable_inbox.setToolTip('Enable search function in the Inbox')
        app_search_layout.addRow('Searchable Inbox', self.searchable_inbox)

        self.search_every_keystroke = QRadioButton('Search on every keystroke *', app_search)
        app_search_layout.addRow(self.search_every_keystroke)
        self.search_on_enter = QRadioButton('Search on return-key *', app_search)
        app_search_layout.addRow(self.search_on_enter)


        # App / General / External Viewer
        app_external_viewer, app_external_viewer_l = groupbox('External Viewer', QFormLayout, application_general, app_general_m_l)
        external_viewer_p_info = QLabel("Tip: If your preferred image viewer doesn't work, try changing the arguments sent in the Advanced section")
        external_viewer_p_info.setWordWrap(True)
        app_external_viewer_l.addRow(external_viewer_p_info)
        self.external_viewer_path = PathLineEdit(app_external_viewer, False, '')
        self.external_viewer_path.setPlaceholderText('Right/Left-click to open folder explorer.'+
                              ' Leave empty to use default viewer')
        self.external_viewer_path.setToolTip('Right/Left-click to open folder explorer.'+
                              ' Leave empty to use default viewer')
        self.external_viewer_path.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        app_external_viewer_l.addRow('Path:', self.external_viewer_path)


        # App / General / Rar Support
        app_rar_group, app_rar_layout = groupbox('RAR Support *', QFormLayout, self)
        app_general_m_l.addRow(app_rar_group)
        rar_info = QLabel('Specify the path to the unrar tool to enable rar support.\n' \
                          'Windows: An "unrar.exe" should be in the "bin" directory if you installed from the self-extracting archive provided on github.\n' \
                          'OSX: You can install this via HomeBrew. The path should be something like: "/usr/local/bin/unrar".\n' \
                          'Linux: Should already be installed as just "unrar". If it\'s not installed, use your package manager: pacman -S unrar')

        rar_info.setWordWrap(True)
        app_rar_layout.addRow(rar_info)
        self.path_to_unrar = PathLineEdit(self, False, filters='')
        app_rar_layout.addRow('UnRAR tool path:', self.path_to_unrar)


        # App / Gallery
        app_gallery_page, app_gallery_l = new_tab('Gallery', application, True)


        # App / Gallery / Default values
        g_def_values, g_def_values_l = groupbox("Default values", QFormLayout, app_gallery_page)
        app_gallery_l.addRow(g_def_values)
        self.g_languages = QComboBox(self)
        self.g_languages.setInsertPolicy(QComboBox.InsertAlphabetically)
        self.g_languages.setEditable(True)
        g_def_values_l.addRow("Default Language", self.g_languages)
        self.g_type = QComboBox(self)
        g_def_values_l.addRow("Default Type", self.g_type)
        self.g_status = QComboBox(self)
        g_def_values_l.addRow("Default Status", self.g_status)


        # App / Gallery / 
        self.subfolder_as_chapters = QCheckBox("Subdirectiories should be treated as standalone galleries instead of chapters (applies in archives too)")
        self.subfolder_as_chapters.setToolTip("This option will enable creating standalone galleries for each subdirectiories found recursively when importing."+
                                              "\nDefault action is treating each subfolder found as chapters of a gallery.")
        extract_gallery_info = QLabel("Note: This option has no effect when turned off if path to external viewer is not specified.")
        self.extract_gallery_before_opening = QCheckBox("Extract archive before opening (Uncheck only if your viewer supports it)")
        self.open_galleries_sequentially = QCheckBox("Open chapters sequentially (Note: has no effect if path to viewer is not specified)")
        subf_info = QLabel("Behaviour of 'Scan for new galleries on startup' option will be affected.")
        subf_info.setWordWrap(True)
        
        app_gallery_l.addRow('Note:', subf_info)
        app_gallery_l.addRow(self.subfolder_as_chapters)
        app_gallery_l.addRow(extract_gallery_info)
        app_gallery_l.addRow(self.extract_gallery_before_opening)
        app_gallery_l.addRow(self.open_galleries_sequentially)


        # App / Gallery / Move imported galleries
        self.move_imported_gs, move_imported_gs_l = groupbox('Move imported galleries', QFormLayout, app_gallery_page)
        self.move_imported_gs.setCheckable(True)
        self.move_imported_gs.setToolTip("Move imported galleries to specified folder.")
        self.move_imported_def_path = PathLineEdit()
        move_imported_gs_l.addRow('Directory:', self.move_imported_def_path)
        app_gallery_l.addRow(self.move_imported_gs)


        # App / Gallery / Rename gallery source
        self.rename_g_source_group, rename_g_source_l = groupbox('Rename gallery source (Coming soon)', QFormLayout, app_gallery_page)
        self.rename_g_source_group.setCheckable(True)
        self.rename_g_source_group.setDisabled(True)
        app_gallery_l.addRow(self.rename_g_source_group)
        rename_g_source_l.addRow(QLabel("Check what to include when renaming gallery source. (Same order)"))
        rename_g_source_flow_l = FlowLayout()
        rename_g_source_l.addRow(rename_g_source_flow_l)
        self.rename_artist = QCheckBox("Artist")
        self.rename_title = QCheckBox("Title")
        self.rename_lang = QCheckBox("Language")
        self.rename_title.setChecked(True)
        self.rename_title.setDisabled(True)
        rename_g_source_flow_l.addWidget(self.rename_artist)
        rename_g_source_flow_l.addWidget(self.rename_title)
        rename_g_source_flow_l.addWidget(self.rename_lang)


        # App / Gallery / New Gallery Fixes
        new_gallery_fixes, new_gallery_fixes_l = groupbox('New Gallery Fixes', QFormLayout, app_gallery_page)
        app_gallery_l.addRow(new_gallery_fixes)
        self.new_gallery_trim_starting_paren_checkbox = QCheckBox('Remove starting parentheses like (C98), (COMIC1☆7), etc. from new galleries', new_gallery_fixes)
        new_gallery_fixes_l.addRow(self.new_gallery_trim_starting_paren_checkbox)
        self.new_gallery_trim_curly = QCheckBox('Remove anything in {curly braces}', new_gallery_fixes)
        new_gallery_fixes_l.addRow(self.new_gallery_trim_curly)
        self.new_gallery_keep_title = QComboBox()
        self.new_gallery_keep_title.addItem('Keep everything', 0)
        self.new_gallery_keep_title.addItem('Keep part before', 1)
        self.new_gallery_keep_title.addItem('Keep part after', 2)
        new_gallery_fixes_l.addRow('For titles split with \'|\':', self.new_gallery_keep_title)


        # App / Gallery / Random Gallery Opener
        random_gallery_opener, random_g_opener_l = groupbox('Random Gallery Opener', QFormLayout, app_gallery_page)
        app_gallery_l.addRow(random_gallery_opener)
        self.open_random_g_chapters = QCheckBox("Open random gallery chapters")
        random_g_opener_l.addRow(self.open_random_g_chapters)


        # App / Monitoring
        app_monitor_page = QScrollArea()
        app_monitor_page.setBackgroundRole(QPalette.Base)
        app_monitor_dummy = QWidget()
        app_monitor_page.setWidgetResizable(True)
        app_monitor_page.setWidget(app_monitor_dummy)
        application.addTab(app_monitor_page, 'Monitoring')
        app_monitor_m_l = QVBoxLayout(app_monitor_dummy)


        # App / Monitoring / General
        app_monitor_misc_group = QGroupBox('General', self)
        app_monitor_m_l.addWidget(app_monitor_misc_group)
        app_monitor_misc_m_l = QFormLayout(app_monitor_misc_group)
        monitor_info = QLabel('Directory monitoring will monitor the specified directories for any filesystem events. ' \
                              'For example if you delete a gallery source in one of your monitored directories the application ' \
                              'will inform you and ask if you want to delete the gallery from the application as well.')

        monitor_info.setWordWrap(True)
        app_monitor_misc_m_l.addRow(monitor_info)
        self.enable_monitor = QCheckBox('Enable directory monitoring')
        app_monitor_misc_m_l.addRow(self.enable_monitor)
        self.look_new_gallery_startup = QCheckBox('Scan for new galleries on startup')
        app_monitor_misc_m_l.addRow(self.look_new_gallery_startup)


        # App / Monitoring / Directories
        app_monitor_group = QGroupBox('Directories', self)
        app_monitor_m_l.addWidget(app_monitor_group, 1)
        app_monitor_folders_m_l = QVBoxLayout(app_monitor_group)
        app_monitor_folders_add = QPushButton('+')
        app_monitor_folders_add.clicked.connect(self.add_folder_monitor)
        app_monitor_folders_add.setMaximumWidth(20)
        app_monitor_folders_add.setMaximumHeight(20)
        app_monitor_folders_m_l.addWidget(app_monitor_folders_add, 0, Qt.AlignRight)
        self.folders_layout = QFormLayout()
        app_monitor_folders_m_l.addLayout(self.folders_layout)


        # App / Ignore
        app_ignore, app_ignore_m_l = new_tab('Ignore', application, True)


        # App / Ignore / Folder & File extensions
        ignore_ext_group, ignore_ext_l = groupbox('Folder && File extensions (Check to ignore)', QVBoxLayout, app_monitor_dummy)
        app_ignore_m_l.addRow(ignore_ext_group)
        ignore_ext_list_l = FlowLayout()
        ignore_ext_l.addLayout(ignore_ext_list_l)
        self.ignore_folder = QCheckBox("Folder", ignore_ext_group)
        ignore_ext_list_l.addWidget(self.ignore_folder)
        self.ignore_zip = QCheckBox("ZIP", ignore_ext_group)
        ignore_ext_list_l.addWidget(self.ignore_zip)
        self.ignore_cbz = QCheckBox("CBZ", ignore_ext_group)
        ignore_ext_list_l.addWidget(self.ignore_cbz)
        self.ignore_rar = QCheckBox("RAR", ignore_ext_group)
        ignore_ext_list_l.addWidget(self.ignore_rar)
        self.ignore_cbr = QCheckBox("CBR", ignore_ext_group)
        ignore_ext_list_l.addWidget(self.ignore_cbr)


        # App / Ignore / List
        app_ignore_group, app_ignore_list_l = groupbox('List', QVBoxLayout, app_monitor_dummy)
        app_ignore_m_l.addRow(app_ignore_group)
        add_buttons_l = QHBoxLayout()
        app_ignore_add_a = QPushButton('Add archive')
        app_ignore_add_a.clicked.connect(lambda: self.add_ignore_path(dir=False))
        app_ignore_add_f = QPushButton('Add directory')
        app_ignore_add_f.clicked.connect(self.add_ignore_path)
        add_buttons_l.addWidget(app_ignore_add_a, 0, Qt.AlignRight)
        add_buttons_l.addWidget(app_ignore_add_f, 1, Qt.AlignRight)
        app_ignore_list_l.addLayout(add_buttons_l)
        self.ignore_path_l = QFormLayout()
        app_ignore_list_l.addLayout(self.ignore_path_l)


        # Web
        web = QTabWidget(self)
        self.web_index = self.right_panel.addWidget(web)


        # Web / Logins
        logins_page, logins_layout = new_tab("Logins", web, True)

        def login(userlineedit, passlineedit, statuslbl, baseHen_class, partial_txt, relogin=False):
            statuslbl.setText("Logging in...")
            statuslbl.show()
            try:
                c_h = baseHen_class.login(userlineedit.text(), passlineedit.text(), relogin)
                result = baseHen_class.check_login(c_h)
                if result == 1:
                    statuslbl.setText("<font color='green'>{}</font>".format(partial_txt))
                elif result:
                    statuslbl.setText("<font color='green'>Logged in!</font>")
                else:
                    statuslbl.setText("<font color='red'>Logging in failed!</font>")
            except app_constants.WrongLogin:
                statuslbl.setText("<font color='red'>Wrong login information!</font>")
        
        def make_login_forms(layout, exprops, baseHen_class, partial_txt='You have partial access!', info=''):
            status = QLabel(logins_page)
            status.setText("<font color='red'>Not logged in!</font>")
            layout.addRow(status)
            user = QLineEdit(logins_page)
            usertxt = 'Username:'
            passtxt = 'Password:'
            if baseHen_class == pewnet.EHen:
                usertxt = 'IPB Member ID:'
                passtxt = 'IPB Pass Hash:'
            layout.addRow(usertxt, user)
            passw = QLineEdit(logins_page)
            layout.addRow(passtxt, passw)
            passw.setEchoMode(QLineEdit.Password)
            log_btn = QPushButton("Login")
            b_l = QHBoxLayout()
            b_l.addWidget(Spacer('h'))
            b_l.addWidget(log_btn)
            layout.addRow(b_l)
            if info:
                layout.addRow(QLabel(info))
            result = baseHen_class.check_login(exprops.cookies)
            if result == 1:
                status.setText("<font color='orange'>{}</font>".format(partial_txt))
            elif result:
                status.setText("<font color='green'>Logged in!</font>")
            if result:
                user.setText(exprops.username)
                passw.setText(exprops.password)
                log_btn.setText("Relogin")
                log_btn.clicked.connect(lambda: login(user, passw, status, baseHen_class, partial_txt, True))
            else:
                log_btn.clicked.connect(lambda: login(user, passw, status, baseHen_class, partial_txt))

            return user, passw, status

        # ehentai
        exprops = settings.ExProperties
        ehentai_group, ehentai_l = groupbox("E-Hentai", QFormLayout, logins_page)
        logins_layout.addRow(ehentai_group)
        ehentai_user, ehentai_pass, ehentai_status = make_login_forms(ehentai_l, exprops(), pewnet.EHen,
                                                                "You have partial access (e-hentai). You do not have access to exhentai.",
                                                                app_constants.EXHEN_COOKIE_TUTORIAL)

        # nhentai
        #nhentai_group, nhentai_l = groupbox("NHentai", QFormLayout, logins_page)
        #logins_layout.addRow(nhentai_group)
        #nhentai_user, nhentai_pass, nhentai_status = make_login_forms(nhentai_l, exprops(exprops.NHENTAI), pewnet.NHen)


        # Web / Downloader
        web_downloader, web_downloader_l = new_tab('Downloader', web)
        hen_download_group, hen_download_group_l = groupbox('E-Hentai', QFormLayout, web_downloader)

        web_downloader_l.addRow(hen_download_group)
        self.archive_download = QRadioButton('Archive', hen_download_group)
        self.torrent_download = QRadioButton('Torrent', hen_download_group)
        download_type_l = QHBoxLayout()
        download_type_l.addWidget(self.archive_download)
        download_type_l.addWidget(self.torrent_download, 1)
        hen_download_group_l.addRow('Download Type:', download_type_l)
        self.download_directory = PathLineEdit(web_downloader)
        web_downloader_l.addRow('Destination:', self.download_directory)
        self.torrent_client = PathLineEdit(web_downloader, False, '')
        web_downloader_l.addRow(QLabel("Leave empty to use default torrent client.\nIt is NOT recommended to import a file while it's still downloading."))

        web_downloader_l.addRow('Torrent client:', self.torrent_client)
        self.download_gallery_lib = QCheckBox("Send downloaded galleries directly to library")
        web_downloader_l.addRow(self.download_gallery_lib)


        # Web / Metadata
        web_metadata_page = QScrollArea()
        web_metadata_page.setBackgroundRole(QPalette.Base)
        web_metadata_page.setWidgetResizable(True)
        web.addTab(web_metadata_page, 'Metadata')
        web_metadata_dummy = QWidget()
        web_metadata_page.setWidget(web_metadata_dummy)
        web_metadata_m_l = QFormLayout(web_metadata_dummy)
        self.default_ehen_url = QRadioButton('e-hentai.org', web_metadata_page)
        self.exhentai_ehen_url = QRadioButton('exhentai.org (login needed)', web_metadata_page)
        ehen_url_l = QHBoxLayout()
        ehen_url_l.addWidget(self.default_ehen_url)
        ehen_url_l.addWidget(self.exhentai_ehen_url, 1)
        web_metadata_m_l.addRow('Default EH:', ehen_url_l)
        self.include_expunged = QCheckBox('Allow fetching from expunged galleries')
        web_metadata_m_l.addRow(self.include_expunged)
        self.continue_a_metadata_fetcher = QCheckBox('Skip galleries that has already been processed in auto metadata fetcher')
        web_metadata_m_l.addRow(self.continue_a_metadata_fetcher)
        self.use_global_ehen_lock = QCheckBox('Use global metadata fetch lock')
        web_metadata_m_l.addRow(self.use_global_ehen_lock)
        self.use_jpn_title = QCheckBox('Apply japanese title instead of english title')
        self.use_jpn_title.setToolTip('Applies the japanese title instead of the english')
        web_metadata_m_l.addRow(self.use_jpn_title)
        time_offset_info = QLabel('A delay between EH requests to avoid getting temp banned.')
        self.web_time_offset = QSpinBox()
        self.web_time_offset.setMaximumWidth(40)
        self.web_time_offset.setMinimum(3)
        self.web_time_offset.setMaximum(99)
        web_metadata_m_l.addRow(time_offset_info)
        web_metadata_m_l.addRow('Delay in seconds:', self.web_time_offset)
        web_metadata_m_l.addRow(QLabel(''))
        replace_metadata_info = QLabel('By default metadata is appended to a gallery.\n' \
                                       'Enabling this option makes it so that a gallery\'s old data ' \
                                       'is deleted and replaced with the new data.')
        replace_metadata_info.setWordWrap(True)
        self.replace_metadata = QCheckBox('Replace all old metadata with new metadata')
        web_metadata_m_l.addRow(replace_metadata_info)
        web_metadata_m_l.addRow(self.replace_metadata)

        def add_replace_options(widget):
            widget.addItem('Always', app_constants.REPLACE_TYPE_ALWAYS)
            widget.addItem('Inbox & new galleries only', app_constants.REPLACE_TYPE_NEWONLY)
            widget.addItem('Never', app_constants.REPLACE_TYPE_NEVER)

        replace_metadata_anyway = QLabel('Selectively replace metadata anyway:')
        replace_metadata_anyway.setWordWrap(True)
        web_metadata_m_l.addRow(replace_metadata_anyway)
        self.always_apply_title = QComboBox(self)
        add_replace_options(self.always_apply_title)
        web_metadata_m_l.addRow('Replace existing title:', self.always_apply_title)
        self.always_apply_artist = QComboBox(self)
        add_replace_options(self.always_apply_artist)
        web_metadata_m_l.addRow('Replace existing artist:', self.always_apply_artist)
        self.always_apply_language = QComboBox(self)
        add_replace_options(self.always_apply_language)
        web_metadata_m_l.addRow('Replace existing language:', self.always_apply_language)
        self.always_apply_g_type = QComboBox(self)
        add_replace_options(self.always_apply_g_type)
        web_metadata_m_l.addRow('Replace existing gallery type:', self.always_apply_g_type)
        self.always_apply_tags = QComboBox(self)
        add_replace_options(self.always_apply_tags)
        web_metadata_m_l.addRow('Replace existing tags:', self.always_apply_tags)

        def toggle_replacement_options():
            self.always_apply_title.setEnabled(not self.replace_metadata.isChecked())
            self.always_apply_artist.setEnabled(not self.replace_metadata.isChecked())
            self.always_apply_language.setEnabled(not self.replace_metadata.isChecked())
            self.always_apply_g_type.setEnabled(not self.replace_metadata.isChecked())
            self.always_apply_tags.setEnabled(not self.replace_metadata.isChecked())

        self.replace_metadata.stateChanged.connect(toggle_replacement_options)
        toggle_replacement_options()

        web_metadata_m_l.addRow(QLabel(''))
        self.always_first_hit = QCheckBox('Always choose first gallery found')
        web_metadata_m_l.addRow(self.always_first_hit)
        use_gallery_link_info = QLabel("Enable this option to fetch metadata using the currently applied URL on the gallery")
        self.use_gallery_link = QCheckBox('Use currently applied gallery URL')
        self.use_gallery_link.setToolTip("Metadata will be fetched from the current gallery URL if it's a supported gallery url")

        web_metadata_m_l.addRow(use_gallery_link_info)
        web_metadata_m_l.addRow(self.use_gallery_link)
        fallback_source_info = QLabel("Specify which sources metadata fetcher should fallback to when a gallery is not found.")
        fallback_source_l = FlowLayout()
        web_metadata_m_l.addRow(fallback_source_info)
        web_metadata_m_l.addRow(fallback_source_l)
        self.fallback_chaika = QCheckBox("panda.chaika.moe")
        fallback_source_l.addWidget(self.fallback_chaika)


        # Visual
        visual = QTabWidget(self)
        self.visual_index = self.right_panel.addWidget(visual)

        # Visual / General
        visual_general_page, visual_general_layout = new_tab('General', visual, True)

        galleryedit_box, galleryedit_box_layout = groupbox('Gallery Edit Dialog', QFormLayout, visual_general_page)
        visual_general_layout.addRow(galleryedit_box)

        self.galleryedit_width = QSpinBox(galleryedit_box)
        self.galleryedit_width.setRange(200, 100000)
        self.galleryedit_width.setFixedWidth(120)
        galleryedit_box_layout.addRow('Dialog Width:', self.galleryedit_width)


        # Visual / Grid View
        grid_view_general_page, grid_view_layout = new_tab("Grid View", visual, True)


        # Visual / Grid View / Popup
        grid_popup, grid_popup_l = groupbox("Popup", QFormLayout, grid_view_general_page)
        grid_view_layout.addRow(grid_popup)
        self.g_popup_width = QSpinBox(grid_popup)
        self.g_popup_width.setRange(200, 100000)
        self.g_popup_width.setFixedWidth(120)
        grid_popup_l.addRow("Popup Width:", self.g_popup_width)
        self.g_popup_height = QSpinBox(grid_popup)
        self.g_popup_height.setRange(100, 1000000)
        self.g_popup_height.setFixedWidth(120)
        grid_popup_l.addRow("Popup Height:", self.g_popup_height)


        # Visual / Grid View / Tooltip
        self.grid_tooltip_group = QGroupBox('Tooltip', grid_view_general_page)
        self.grid_tooltip_group.setCheckable(True)
        grid_view_layout.addRow(self.grid_tooltip_group)
        grid_tooltip_layout = QFormLayout()
        self.grid_tooltip_group.setLayout(grid_tooltip_layout)
        grid_tooltip_layout.addRow(QLabel('Control what is displayed in the tooltip when hovering a gallery'))

        grid_tooltips_hlayout = FlowLayout()
        grid_tooltip_layout.addRow(grid_tooltips_hlayout)
        self.visual_grid_tooltip_title = QCheckBox('Title')
        grid_tooltips_hlayout.addWidget(self.visual_grid_tooltip_title)
        self.visual_grid_tooltip_author = QCheckBox('Author')
        grid_tooltips_hlayout.addWidget(self.visual_grid_tooltip_author)
        self.visual_grid_tooltip_chapters = QCheckBox('Chapters')
        grid_tooltips_hlayout.addWidget(self.visual_grid_tooltip_chapters)
        self.visual_grid_tooltip_status = QCheckBox('Status')
        grid_tooltips_hlayout.addWidget(self.visual_grid_tooltip_status)
        self.visual_grid_tooltip_type = QCheckBox('Type')
        grid_tooltips_hlayout.addWidget(self.visual_grid_tooltip_type)
        self.visual_grid_tooltip_lang = QCheckBox('Language')
        grid_tooltips_hlayout.addWidget(self.visual_grid_tooltip_lang)
        self.visual_grid_tooltip_descr = QCheckBox('Description')
        grid_tooltips_hlayout.addWidget(self.visual_grid_tooltip_descr)
        self.visual_grid_tooltip_tags = QCheckBox('Tags')
        grid_tooltips_hlayout.addWidget(self.visual_grid_tooltip_tags)
        self.visual_grid_tooltip_last_read = QCheckBox('Last read')
        grid_tooltips_hlayout.addWidget(self.visual_grid_tooltip_last_read)
        self.visual_grid_tooltip_times_read = QCheckBox('Times read')
        grid_tooltips_hlayout.addWidget(self.visual_grid_tooltip_times_read)
        self.visual_grid_tooltip_pub_date = QCheckBox('Publication Date')
        grid_tooltips_hlayout.addWidget(self.visual_grid_tooltip_pub_date)
        self.visual_grid_tooltip_date_added = QCheckBox('Date added')
        grid_tooltips_hlayout.addWidget(self.visual_grid_tooltip_date_added)


        # Visual / Grid View / Gallery
        grid_gallery_group = QGroupBox('Gallery', grid_view_general_page)
        grid_view_layout.addRow(grid_gallery_group)
        grid_gallery_main_l = QFormLayout()
        grid_gallery_main_l.setFormAlignment(Qt.AlignLeft)
        grid_gallery_group.setLayout(grid_gallery_main_l)
        grid_gallery_display = FlowLayout()
        grid_gallery_main_l.addRow('Display on gallery:', grid_gallery_display)
        self.gallery_rating = QCheckBox('Rating')
        grid_gallery_display.addWidget(self.gallery_rating)
        self.gallery_type_ico = QCheckBox('File Type')
        grid_gallery_display.addWidget(self.gallery_type_ico)
        if sys.platform.startswith('darwin'):
            self.gallery_rating.setEnabled(False)
            self.gallery_type_ico.setEnabled(False)
        gallery_text_mode = QWidget()
        grid_gallery_main_l.addRow('Text Mode:', gallery_text_mode)
        gallery_text_mode_l = QHBoxLayout()
        gallery_text_mode.setLayout(gallery_text_mode_l)
        self.gallery_text_elide = QRadioButton('Elide text', gallery_text_mode)
        self.gallery_text_fit = QRadioButton('Fit text', gallery_text_mode)
        gallery_text_mode_l.addWidget(self.gallery_text_elide, 0, Qt.AlignLeft)
        gallery_text_mode_l.addWidget(self.gallery_text_fit, 0, Qt.AlignLeft)
        gallery_text_mode_l.addWidget(Spacer('h'), 1, Qt.AlignLeft)
        gallery_font = QHBoxLayout()
        grid_gallery_main_l.addRow('Font:*', gallery_font)
        self.font_lbl = QLabel()
        self.font_size_lbl = QSpinBox()
        self.font_size_lbl.setMaximum(100)
        self.font_size_lbl.setMinimum(1)
        self.font_size_lbl.setToolTip('Font size in pixels')
        choose_font = QPushButton('Choose font')
        choose_font.clicked.connect(self.choose_font)
        gallery_font.addWidget(self.font_lbl, 0, Qt.AlignLeft)
        gallery_font.addWidget(self.font_size_lbl, 0, Qt.AlignLeft)
        gallery_font.addWidget(choose_font, 0, Qt.AlignLeft)
        gallery_font.addWidget(Spacer('h'), 1, Qt.AlignLeft)

        gallery_size_lbl = QLabel(self)
        self.gallery_size = QSlider(Qt.Horizontal, self)
        self.gallery_size.wheelEvent = lambda event: event.ignore()
        self.gallery_size.valueChanged.connect(lambda x: gallery_size_lbl.setText(str(x+2)))
        self.gallery_size.setMinimum(-2)
        self.gallery_size.setMaximum(10)
        self.gallery_size.setSingleStep(1)
        self.gallery_size.setPageStep(3)
        self.gallery_size.setTickInterval(1)
        self.gallery_size.setTickPosition(QSlider.TicksBothSides)
        self.gallery_size.setToolTip("Changes size of grid in gridview. Remember to re-generate thumbnails! DEFAULT=3")
        gallery_size_l = QHBoxLayout()
        gallery_size_l.addWidget(gallery_size_lbl)
        gallery_size_l.addWidget(self.gallery_size)
        grid_gallery_main_l.addRow(QLabel("Note: A manual re-generation of thumbnails is required. Advanced -> Gallery"))
        grid_gallery_main_l.addRow("Thumbnail Size:*", gallery_size_l)
        self.grid_spacing = QSpinBox(self)
        self.grid_spacing.setMinimum(1)
        self.grid_spacing.setMaximum(99)
        self.grid_spacing.setToolTip("Changes space between thumbnails in gridview. DEFAULT=15")
        self.grid_spacing.adjustSize()
        self.grid_spacing.setFixedWidth(self.grid_spacing.width())
        grid_gallery_main_l.addRow("Spacing:*", self.grid_spacing)


        # Visual / Grid View / Colors
        grid_colors_group = QGroupBox('Colors', grid_view_general_page)
        grid_view_layout.addRow(grid_colors_group)
        grid_colors_l = QFormLayout()
        grid_colors_group.setLayout(grid_colors_l)

        def color_lineedit():
            l = QLineEdit()
            l.setPlaceholderText('Hex colors. Eg.: #323232')
            l.setMaximumWidth(200)
            return l

        self.grid_label_color, hbox_layout = self._get_color_line_edit_and_hbox_layout(hex_color=app_constants.GRID_VIEW_LABEL_COLOR)
        grid_colors_l.addRow('Label color:', hbox_layout)
        self.grid_title_color, hbox_layout = self._get_color_line_edit_and_hbox_layout(hex_color=app_constants.GRID_VIEW_TITLE_COLOR)
        grid_colors_l.addRow('Title color:', hbox_layout)
        self.grid_artist_color, hbox_layout = self._get_color_line_edit_and_hbox_layout(hex_color=app_constants.GRID_VIEW_ARTIST_COLOR)
        grid_colors_l.addRow('Artist color:', hbox_layout)


        # Visual / Grid View / Colors / Ribbon
        self.colors_ribbon_group, colors_ribbon_l = groupbox('Ribbon', QFormLayout, grid_colors_group)
        self.colors_ribbon_group.setCheckable(True)
        grid_colors_l.addRow(self.colors_ribbon_group)

        self.ribbon_manga_color, hbox_layout = self._get_color_line_edit_and_hbox_layout(app_constants.GRID_VIEW_T_MANGA_COLOR)
        colors_ribbon_l.addRow('Manga', hbox_layout)
        self.ribbon_doujin_color, hbox_layout = self._get_color_line_edit_and_hbox_layout(app_constants.GRID_VIEW_T_DOUJIN_COLOR)
        colors_ribbon_l.addRow('Doujinshi', hbox_layout)
        self.ribbon_artist_cg_color, hbox_layout = self._get_color_line_edit_and_hbox_layout(app_constants.GRID_VIEW_T_ARTIST_CG_COLOR)
        colors_ribbon_l.addRow('Artist CG', hbox_layout)
        self.ribbon_game_cg_color, hbox_layout = self._get_color_line_edit_and_hbox_layout(app_constants.GRID_VIEW_T_GAME_CG_COLOR)
        colors_ribbon_l.addRow('Game CG', hbox_layout)
        self.ribbon_western_color, hbox_layout = self._get_color_line_edit_and_hbox_layout(app_constants.GRID_VIEW_T_WESTERN_COLOR)
        colors_ribbon_l.addRow('Western', hbox_layout)
        self.ribbon_image_color, hbox_layout = self._get_color_line_edit_and_hbox_layout(app_constants.GRID_VIEW_T_IMAGE_COLOR)
        colors_ribbon_l.addRow('Image', hbox_layout)
        self.ribbon_non_h_color, hbox_layout = self._get_color_line_edit_and_hbox_layout(app_constants.GRID_VIEW_T_NON_H_COLOR)
        colors_ribbon_l.addRow('Non-H', hbox_layout)
        self.ribbon_cosplay_color, hbox_layout = self._get_color_line_edit_and_hbox_layout(app_constants.GRID_VIEW_T_COSPLAY_COLOR)
        colors_ribbon_l.addRow('Cosplay', hbox_layout)
        self.ribbon_other_color, hbox_layout = self._get_color_line_edit_and_hbox_layout(app_constants.GRID_VIEW_T_OTHER_COLOR)
        colors_ribbon_l.addRow('Other', hbox_layout)

        # Visual / Style
        style_page = QWidget(self)
        visual.addTab(style_page, 'Style')

        # disable tab "Style"
        visual.setTabEnabled(2, False)
        # start at "Grid View"
        visual.setCurrentIndex(1)


        # Advanced
        advanced = QTabWidget(self)
        self.advanced_index = self.right_panel.addWidget(advanced)


        # Advanced / Misc
        advanced_misc_scroll = QScrollArea(self)
        advanced_misc_scroll.setBackgroundRole(QPalette.Base)
        advanced_misc_scroll.setWidgetResizable(True)
        advanced_misc = QWidget()
        advanced_misc_scroll.setWidget(advanced_misc)
        advanced.addTab(advanced_misc_scroll, 'Misc')
        advanced_misc_main_layout = QVBoxLayout()
        advanced_misc.setLayout(advanced_misc_main_layout)
        misc_controls_layout = QFormLayout()
        advanced_misc_main_layout.addLayout(misc_controls_layout)

        high_dpi_info = QLabel("Warning: This option may incur some scaling or painting artifacts")
        misc_controls_layout.addRow(high_dpi_info)
        self.force_high_dpi_support = QCheckBox("Force High DPI support *", self)
        misc_controls_layout.addRow(self.force_high_dpi_support)


        # Advanced / Misc / External Viewer Arguments
        external_view_group, external_view_l = groupbox("External Viewer Arguments", QFormLayout, advanced)
        misc_controls_layout.addRow(external_view_group)
        external_viewer_info = QLabel(app_constants.EXTERNAL_VIEWER_INFO)
        external_viewer_info.setWordWrap(True)
        self.external_viewer_args = QLineEdit(advanced)
        external_view_l.addRow("Available tokens:", external_viewer_info)
        external_view_l.addRow("Arguments:", self.external_viewer_args)


        # Advanced / Misc / Grid View
        misc_gridview = QGroupBox('Grid View')
        misc_controls_layout.addRow(misc_gridview)
        misc_gridview_layout = QFormLayout()
        misc_gridview.setLayout(misc_gridview_layout)


        # Advanced / Misc / Grid View / scroll speed
        scroll_speed_spin_box = QSpinBox()
        scroll_speed_spin_box.setFixedWidth(60)
        scroll_speed_spin_box.setToolTip('Control the speed when scrolling in grid view. DEFAULT: 7')
        scroll_speed_spin_box.setValue(self.scroll_speed)
        def scroll_speed(v): self.scroll_speed = v
        scroll_speed_spin_box.valueChanged[int].connect(scroll_speed)
        misc_gridview_layout.addRow('Scroll speed:', scroll_speed_spin_box)


        # Advanced / Misc / Grid View / cache size
        cache_size_spin_box = QSpinBox()
        cache_size_spin_box.setFixedWidth(120)
        cache_size_spin_box.setMaximum(999999999)
        cache_size_spin_box.setToolTip('This can greatly reduce lags/freezes in the grid view. ' \
                                       'Increase the value if you experience lag when scrolling through galleries. ' \
                                       'DEFAULT: 200 MiB')
        def cache_size(c): self.cache_size = (self.cache_size[0], c)
        cache_size_spin_box.setValue(self.cache_size[1])
        cache_size_spin_box.valueChanged[int].connect(cache_size)
        misc_gridview_layout.addRow('Cache Size (MiB):', cache_size_spin_box)


        # Advanced / Gallery
        advanced_gallery, advanced_gallery_m_l = new_tab('Gallery', advanced)
        def rebuild_thumbs():
            confirm_msg = QMessageBox(QMessageBox.Question, '', 'Are you sure you want to regenerate your thumbnails.',
                             QMessageBox.Yes | QMessageBox.No, self)
            if confirm_msg.exec() == QMessageBox.Yes:
                clear_cache_confirm = QMessageBox(QMessageBox.Question, '',
                                      'Do you want to delete all old thumbnails before regenerating?', QMessageBox.Yes | QMessageBox.No,
                                      self)
                clear_cache = False
                if clear_cache_confirm.exec() == QMessageBox.Yes:
                    clear_cache = True
                app_spinner = misc.Spinner(self.parent_widget)
                app_spinner.set_size(60)
                app_spinner.set_text("Thumbnails")
                app_spinner.admin_db = gallerydb.AdminDB()
                app_spinner.admin_db.moveToThread(app_constants.GENERAL_THREAD)
                app_spinner.admin_db.DONE.connect(app_spinner.admin_db.deleteLater)
                app_spinner.admin_db.DONE.connect(app_spinner.before_hide)
                self.init_gallery_rebuild.connect(app_spinner.admin_db.rebuild_thumbs)
                self.init_gallery_rebuild.emit(clear_cache)
                app_spinner.show()

        rebuild_thumbs_info = QLabel("Clears thumbnail cache and rebuilds it, which can take a while. Tip: Useful when changing thumbnail size.")
        rebuild_thumbs_btn = QPushButton('Regenerate Thumbnails')
        rebuild_thumbs_btn.adjustSize()
        rebuild_thumbs_btn.setFixedWidth(rebuild_thumbs_btn.width())
        rebuild_thumbs_btn.clicked.connect(rebuild_thumbs)
        advanced_gallery_m_l.addRow(rebuild_thumbs_info)
        advanced_gallery_m_l.addRow(rebuild_thumbs_btn)


        # Advanced / Gallery / Gallery Renamer
        g_data_fixer_group, g_data_fixer_l =  groupbox('Gallery Renamer', QFormLayout, advanced_gallery)
        g_data_fixer_group.setEnabled(False)
        advanced_gallery_m_l.addRow(g_data_fixer_group)
        g_data_regex_fix_lbl = QLabel("Rename a gallery through regular expression. A regex cheatsheet is located at About -> Regex Cheatsheet.")
        g_data_regex_fix_lbl.setWordWrap(True)
        g_data_fixer_l.addRow(g_data_regex_fix_lbl)
        self.g_data_regex_fix_edit = QLineEdit()
        self.g_data_regex_fix_edit.setPlaceholderText("Valid regex")
        g_data_fixer_l.addRow('Regex:', self.g_data_regex_fix_edit)
        self.g_data_replace_fix_edit = QLineEdit()
        self.g_data_replace_fix_edit.setPlaceholderText("Leave empty to delete matches")
        g_data_fixer_l.addRow('Replace with:', self.g_data_replace_fix_edit)
        g_data_fixer_options = FlowLayout()
        g_data_fixer_l.addRow(g_data_fixer_options)
        self.g_data_fixer_title = QCheckBox("Title", g_data_fixer_group)
        self.g_data_fixer_artist = QCheckBox("Artist", g_data_fixer_group)
        g_data_fixer_options.addWidget(self.g_data_fixer_title)
        g_data_fixer_options.addWidget(self.g_data_fixer_artist)


        # Advanced / Database
        advanced_db_page, advanced_db_page_l = new_tab('Database', advanced)


        # Advanced / Database / Import/Export
        def init_export():
            confirm_msg = QMessageBox(QMessageBox.Question, '', 'Are you sure you want to export your database?', QMessageBox.Yes | QMessageBox.No, self)
            if confirm_msg.exec() == QMessageBox.Yes:
                app_popup = AppDialog(self.parent_widget)
                app_popup.info_lbl.setText("Exporting database...")
                app_popup.export_instance = io_misc.ImportExport()
                app_popup.export_instance.moveToThread(app_constants.GENERAL_THREAD)
                app_popup.export_instance.finished.connect(app_popup.export_instance.deleteLater)
                app_popup.export_instance.finished.connect(app_popup.close)
                app_popup.export_instance.amount.connect(app_popup.prog.setMaximum)
                app_popup.export_instance.progress.connect(app_popup.prog.setValue)
                self.init_gallery_eximport.connect(app_popup.export_instance.export_data)
                self.init_gallery_eximport.emit(None)
                app_popup.adjustSize()
                app_popup.show()
                self.close()

        def init_import():
            path = QFileDialog.getOpenFileName(self, 'Choose happypanda database file', filter='*.hpdb')
            path = path[0]
            if len(path) != 0:
                app_popup = AppDialog(self.parent_widget)
                app_popup.restart_info.hide()
                app_popup.info_lbl.setText("Importing database file...")
                app_popup.note_info.setText("Application requires a restart after importing")
                app_popup.import_instance = io_misc.ImportExport()
                app_popup.import_instance.moveToThread(app_constants.GENERAL_THREAD)
                app_popup.import_instance.finished.connect(app_popup.import_instance.deleteLater)
                app_popup.import_instance.finished.connect(app_popup.init_restart)
                app_popup.import_instance.amount.connect(app_popup.prog.setMaximum)
                app_popup.import_instance.imported_g.connect(app_popup.info_lbl.setText)
                app_popup.import_instance.progress.connect(app_popup.prog.setValue)
                self.init_gallery_eximport.connect(app_popup.import_instance.import_data)
                self.init_gallery_eximport.emit(path)
                app_popup.adjustSize()
                app_popup.show()
                self.close()

        advanced_impexp, advanced_impexp_l = groupbox('Import/Export', QFormLayout, advanced_db_page)
        advanced_db_page_l.addRow(advanced_impexp)

        self.export_format = QComboBox(advanced_db_page)
        #self.export_format.addItem('Text File', 0)
        self.export_format.addItem('HPDB', 1)
        self.export_format.adjustSize()
        self.export_format.setFixedWidth(self.export_format.width())
        advanced_impexp_l.addRow('Export Format:', self.export_format)
        self.export_path = PathLineEdit(advanced_impexp, filters='')
        advanced_impexp_l.addRow('Export Path:', self.export_path)
        import_btn = QPushButton('Import database')
        import_btn.clicked.connect(init_import)
        export_btn = QPushButton('Export database')
        export_btn.clicked.connect(init_export)
        ex_imp_btn_l = QHBoxLayout()
        ex_imp_btn_l.addWidget(import_btn)
        ex_imp_btn_l.addWidget(export_btn)
        advanced_impexp_l.addRow(ex_imp_btn_l)


        # Advanced / Database / Startup
        advanced_dbstartup, advanced_dbstartup_l = groupbox('Startup', QFormLayout, advanced_db_page)
        advanced_db_page_l.addRow(advanced_dbstartup)

        self.advanced_dbstartup_fetch_limit_spinbox = QSpinBox(advanced_db_page)
        self.advanced_dbstartup_fetch_limit_spinbox.setMinimum(0)
        self.advanced_dbstartup_fetch_limit_spinbox.setMaximum(1_000_000)
        self.advanced_dbstartup_fetch_limit_spinbox.setValue(app_constants.DATABASE_STARTUP_FETCH_LIMIT)
        self.advanced_dbstartup_fetch_limit_spinbox.setToolTip('Batch size of galleries that is fetched from the database upon startup.\n' \
                                                          'Higher number means faster loading. 0 means no limit, but the app may appear stuck for a few seconds.\n' \
                                                          'DEFAULT: 1000')
        advanced_dbstartup_l.addRow('Startup gallery fetch limit:', self.advanced_dbstartup_fetch_limit_spinbox)


        # About
        about = QTabWidget(self)
        self.about_index = self.right_panel.addWidget(about)
        about_happypanda_page, about_layout = new_tab("About Happypanda", about, False)
        info_lbl = QLabel(app_constants.ABOUT)
        info_lbl.setWordWrap(True)
        info_lbl.setOpenExternalLinks(True)
        about_layout.addWidget(info_lbl)
        about_layout.addWidget(Spacer('v'))
        open_hp_folder = QPushButton('Open Happypanda Directory')
        open_hp_folder.clicked.connect(self.open_hp_folder)
        open_hp_folder.adjustSize()
        open_hp_folder.setFixedWidth(open_hp_folder.width())
        about_layout.addWidget(open_hp_folder)


        ## About / DB Overview
        #about_db_overview, about_db_overview_m_l = new_tab('DB Overview', about)
        #about_stats_tab_widget = misc_db.DBOverview(self.parent_widget)
        #about_db_overview_m_l.addRow(about_stats_tab_widget)
        #about_db_overview.setEnabled(False)


        # About / Troubleshooting
        about_troubleshoot_page = QWidget()
        about.addTab(about_troubleshoot_page, 'Bug Reporting')
        troubleshoot_layout = QVBoxLayout()
        about_troubleshoot_page.setLayout(troubleshoot_layout)
        guide_lbl = QLabel(app_constants.TROUBLE_GUIDE)
        guide_lbl.setTextFormat(Qt.RichText)
        guide_lbl.setOpenExternalLinks(True)
        guide_lbl.setWordWrap(True)
        troubleshoot_layout.addWidget(guide_lbl, 0, Qt.AlignTop)
        troubleshoot_layout.addWidget(Spacer('v'))


        # About / Search Guide
        about_search_tut, about_search_tut_l = new_tab("Search Guide", about, True)
        g_search_lbl = QLabel(app_constants.SEARCH_TUTORIAL_TAGS)
        g_search_lbl.setWordWrap(True)
        about_search_tut_l.addRow(g_search_lbl)


        # About / Regex Cheatsheet
        about_s_regex, about_s_regex_l = new_tab("Regex Cheatsheet", about, True)
        reg_info = QLabel(app_constants.REGEXCHEAT)
        reg_info.setWordWrap(True)
        about_s_regex_l.addRow(reg_info)


        # About / Keyboard Shortcuts
        about_k_shortcuts, about_k_shortcuts_l = new_tab("Keyboard Shortcuts", about, True)
        k_short_info = QLabel(app_constants.KEYBOARD_SHORTCUTS_INFO)
        k_short_info.setWordWrap(True)
        about_k_shortcuts_l.addRow(k_short_info)

    @staticmethod
    def _get_color_line_edit_and_hbox_layout(hex_color=None):
        """get ColorLineEdit and hbox layout."""
        color_line_edit = ColorLineEdit(hex_color=hex_color)
        hbox_layout = QHBoxLayout()
        hbox_layout.addWidget(color_line_edit)
        hbox_layout.addWidget(color_line_edit.button)
        return color_line_edit, hbox_layout

    def add_folder_monitor(self, path=''):
        if not isinstance(path, str):
            path = ''
        l_edit = PathLineEdit()
        l_edit.setText(path)
        n = self.folders_layout.rowCount() + 1
        self.folders_layout.addRow('{}'.format(n), l_edit)

    def add_ignore_path(self, path='', dir=True):
        if not isinstance(path, str):
            path = ''
        l_edit = PathLineEdit(dir=dir)
        l_edit.setText(path)
        n = self.ignore_path_l.rowCount() + 1
        self.ignore_path_l.addRow('{}'.format(n), l_edit)

    def color_checker(self, txt):
        allow = False
        if len(txt) == 7:
            if txt[0] == '#':
                allow = True
        return allow

    def take_all_layout_widgets(self, l):
        n = l.rowCount()
        items = []
        for x in range(n):
            item = l.takeAt(x+1)
            items.append(item.widget())
        return items

    def choose_font(self):
        tup = QFontDialog.getFont(self)
        font = tup[0]
        if tup[1]:
            self.font_lbl.setText(font.family())
            self.font_size_lbl.setValue(font.pointSize())

    def open_hp_folder(self):
        if os.name == 'posix':
            utils.open_path(app_constants.posix_program_dir)
        else:
            utils.open_path(os.getcwd())

    def reject(self):
        self.close()

    def _find_combobox_match(self, combobox, key, default):
        f_index = combobox.findText(key, Qt.MatchFixedString)
        if f_index != -1:
            combobox.setCurrentIndex(f_index)
        else:
            combobox.setCurrentIndex(default)


