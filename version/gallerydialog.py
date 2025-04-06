import os, threading, logging
from datetime import datetime
from typing import Any

from PyQt5.QtWidgets import (QFrame, QGridLayout, QLayout, QStyle, QWidget, QVBoxLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, QProgressBar, QTextEdit, QComboBox,
                             QDateEdit, QFileDialog, QMessageBox, QCheckBox, QSizePolicy, QSpinBox)
from PyQt5.QtCore import (QPoint, QRect, Qt, QDate, QThread, QTimer, QObject)
from PyQt5.QtGui import QShowEvent

import app
import app_constants
import utils
import gallerydb
import fetch
import misc
import database
import settings
import pewnet

log = logging.getLogger(__name__)
log_i = log.info
log_d = log.debug
log_w = log.warning
log_e = log.error
log_c = log.critical

class GalleryDialog(QWidget):
    """
    A window for adding/modifying gallery.
    Pass a list of QModelIndexes to edit their data
    or pass a path to preset path
    """
    def __init__(self, parent: 'app.AppWindow', arg: str | gallerydb.Gallery | list[gallerydb.Gallery] = None, is_new_gallery=False):
        super().__init__(parent, Qt.Dialog)

        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAutoFillBackground(True)
        m_l = QVBoxLayout()

        self.frame = QFrame()
        self.frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.main_layout = QVBoxLayout()
        self.frame.setLayout(self.main_layout)
        m_l.addWidget(self.frame, 3)

        final_buttons = QHBoxLayout()
        final_buttons.setAlignment(Qt.AlignRight)
        m_l.addLayout(final_buttons)
        self.done = QPushButton("Done")
        self.done.setDefault(True)
        self.cancel = QPushButton("Cancel")
        final_buttons.addWidget(self.cancel)
        final_buttons.addWidget(self.done)
        self._multiple_galleries = False
        self._edit_galleries = []
        self._new_single_gallery = is_new_gallery

        self._gallery_dialog_type = 0

        # single: single url, single fetch thread
        #    all: make parent do it
        self.get_metadata_type = 'single'

        # for comparison in set_web_metadata()
        self.url_for_metadata = ''

        def new_gallery():
            self.setWindowTitle('Add a new gallery')
            self.newUI()
            self.commonUI()
            self.done.clicked.connect(self.accept)
            self.cancel.clicked.connect(self.reject)

        if arg:
            if isinstance(arg, (list, gallerydb.Gallery)):
                if isinstance(arg, gallerydb.Gallery):
                    # editing a single existing gallery
                    self.setWindowTitle('Edit gallery')
                    self._edit_galleries.append(arg)
                else:
                    # multi-gallery edit
                    self.setWindowTitle('Edit {} galleries'.format(len(arg)))
                    self._multiple_galleries = True
                    self._edit_galleries.extend(arg)

                self.commonUI()
                self.setGallery(arg)
                self.done.clicked.connect(self.accept_edit)
                self.cancel.clicked.connect(self.reject_edit)

            elif isinstance(arg, str):
                # new gallery from file path
                new_gallery()
                self.choose_dir(arg)

        else:
            # new gallery without pre-selected file
            new_gallery()
            self._new_single_gallery = True

        # the Frame will figure out its own minimum height based on this width and its children's size policies
        self.resize(app_constants.GALLERY_EDIT_WIDTH, 400)

        log_d('GalleryDialog: Create UI: successful')
        self.setLayout(m_l)
        frect = self.frameGeometry()
        frect.moveCenter(self.parent().geometry().center())
        self.move(frect.topLeft())
        self.parent().gallery_dialog_group.register(self, arg)
        self._fetch_thread = None

    def commonUI(self):
        if not self._multiple_galleries:
            f_web = QGroupBox("Metadata from the Web")
            f_web.setCheckable(False)
            self.main_layout.addWidget(f_web, 0)
            web_main_layout = QVBoxLayout()
            web_info = misc.ClickedLabel("Which gallery URLs are supported? (hover)", parent=self)
            web_info.setToolTip(app_constants.SUPPORTED_METADATA_URLS)
            web_info.setToolTipDuration(999999999)
            web_main_layout.addWidget(web_info, 0)
            self.web_layout = QHBoxLayout()
            web_main_layout.addLayout(self.web_layout, 1)
            f_web.setLayout(web_main_layout)

            url_lbl = QLabel("URL:")
            self.url_edit = QLineEdit()
            self.url_btn = QPushButton("Get metadata")
            self.url_prog = QProgressBar()

            self.url_btn.clicked.connect(self.url_btn_clicked)

            self.url_prog.setTextVisible(False)
            self.url_prog.setMinimum(0)
            self.url_prog.setMaximum(0)
            self.web_layout.addWidget(url_lbl, 0, Qt.AlignLeft)
            self.web_layout.addWidget(self.url_edit, 0)
            self.web_layout.addWidget(self.url_btn, 0, Qt.AlignRight)
            self.web_layout.addWidget(self.url_prog, 0, Qt.AlignRight)
            self.url_edit.setPlaceholderText("Insert supported gallery URLs or just press the button!")
            self.url_prog.hide()

        f_gallery = QGroupBox("Gallery Info")
        f_gallery.setCheckable(False)
        self.main_layout.addWidget(f_gallery, 1)
        # gallery_layout = QFormLayout()
        gallery_layout = QGridLayout()
        f_gallery.setLayout(gallery_layout)

        def checkbox_layout(widget: QWidget):
            # if self._multiple_galleries:
            #     l = QHBoxLayout()
            #     l.addWidget(widget.g_check)
            #     # widget.setSizePolicy(hor_size_policy, ver_size_policy)
            #     l.addWidget(widget)
            #     return l
            # else:
            #     widget.g_check.setChecked(True)
            #     widget.g_check.hide()
            #     return widget
            l = QHBoxLayout()
            l.addWidget(widget.g_check)
            l.addWidget(widget)
            if not self._multiple_galleries:
                widget.g_check.setChecked(True)
                widget.g_check.hide()
            return l

        def add_check(widget) -> QWidget:
            widget.g_check = QCheckBox(self)
            return widget

        self.title_edit = add_check(QLineEdit())
        self.title_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.author_edit = add_check(QLineEdit())
        author_completer = misc.GCompleter(self, False, True, False)
        author_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.author_edit.setCompleter(author_completer)
        self.author_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.descr_edit = add_check(QTextEdit())
        self.descr_edit.setAcceptRichText(True)
        self.descr_edit.setTabChangesFocus(True)
        self.descr_edit.setMinimumHeight(40)
        self.descr_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)

        self.lang_box = add_check(QComboBox())
        self.lang_box.addItems(app_constants.G_LANGUAGES)
        self.lang_box.addItems(app_constants.G_CUSTOM_LANGUAGES)
        self.lang_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.rating_box = add_check(QSpinBox())
        self.rating_box.setMaximum(5)
        self.rating_box.setMinimum(0)
        self.rating_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._find_combobox_match(self.lang_box, app_constants.G_DEF_LANGUAGE, 0)
        tags_l = QVBoxLayout()
        tag_info = misc.ClickedLabel("How do i write namespace & tags? (hover)", parent=self)
        tag_info.setToolTip("Ways to write tags:\n\nNormal tags:\ntag1, tag2, tag3\n\n"+
                      "Namespaced tags:\nns1:tag1, ns1:tag2\n\nNamespaced tags with one or more"+
                      " tags under same namespace:\nns1:[tag1, tag2, tag3], ns2:[tag1, tag2]\n\n"+
                      "Those three ways of writing namespace & tags can be combined freely.\n"+
                      "Tags are seperated by a comma, NOT whitespace.\nNamespaces will be capitalized while tags"+
                      " will be lowercased.")
        tag_info.setToolTipDuration(99999999)
        tag_info.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        tags_l.addWidget(tag_info)
        self.tags_edit = add_check(misc.CompleterTextEdit())
        self.tags_edit.setCompleter(misc.GCompleter(self, False, False))
        self.tags_edit.setTabChangesFocus(True)
        self.tags_edit.setPlaceholderText("Press Tab to autocomplete (Ctrl + E to show popup)")
        self.tags_edit.setMinimumHeight(60)
        self.tags_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        if self._multiple_galleries:
            self.tags_edit.g_check.setChecked(True)

        self.tags_append = QCheckBox("Append tags", self)
        self.tags_append.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if not self._multiple_galleries:
            self.tags_append.hide()
        if self._multiple_galleries:
            self.tags_append.setChecked(app_constants.APPEND_TAGS_GALLERIES)
            tags_ml = QVBoxLayout()
            tags_ml.addWidget(self.tags_append)
            tags_ml.addLayout(checkbox_layout(self.tags_edit), 5)
            tags_l.addLayout(tags_ml, 3)
        else:
            tags_l.addLayout(checkbox_layout(self.tags_edit), 5)

        self.type_box = add_check(QComboBox())
        self.type_box.addItems(app_constants.G_TYPES)
        self._find_combobox_match(self.type_box, app_constants.G_DEF_TYPE, 0)
        #self.type_box.currentIndexChanged[int].connect(self.doujin_show)
        #self.doujin_parent = QLineEdit()
        #self.doujin_parent.setVisible(False)
        self.type_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.status_box = add_check(QComboBox())
        self.status_box.addItems(app_constants.G_STATUS)
        self._find_combobox_match(self.status_box, app_constants.G_DEF_STATUS, 0)
        self.status_box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.pub_edit = add_check(QDateEdit())
        self.pub_edit.setCalendarPopup(True)
        self.pub_edit.setDate(QDate.currentDate())
        self.pub_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.path_lbl = misc.ClickedLabel("")
        self.path_lbl.setWordWrap(True)
        self.path_lbl.clicked.connect(lambda a: utils.open_path(a, a) if a else None)
        self.path_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        link_layout = QHBoxLayout()
        self.link_lbl = add_check(QLabel(""))
        self.link_lbl.setWordWrap(True)
        self.link_edit = QLineEdit()
        link_layout.addWidget(self.link_edit)
        if self._multiple_galleries:
            link_layout.addLayout(checkbox_layout(self.link_lbl))
        else:
            link_layout.addLayout(checkbox_layout(self.link_lbl))
        self.link_edit.hide()
        self.link_btn = QPushButton("Modify")
        self.link_btn.setFixedWidth(50)
        self.link_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.link_btn2 = QPushButton("Set")
        self.link_btn2.setFixedWidth(40)
        self.link_btn2.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.link_btn.clicked.connect(self.link_modify)
        self.link_btn2.clicked.connect(self.link_set)
        link_layout.addWidget(self.link_btn)
        link_layout.addWidget(self.link_btn2)
        self.link_btn2.hide()
        
        rating_ = checkbox_layout(self.rating_box)
        lang_ = checkbox_layout(self.lang_box)
        if self._multiple_galleries:
            rating_.insertWidget(0, QLabel("Rating:"))
            lang_.addLayout(rating_)
            lang_l = lang_
        else:
            lang_l = QHBoxLayout()
            lang_l.addLayout(lang_)
            lang_l.addWidget(QLabel("Rating:"), 0, Qt.AlignRight)
            lang_l.addLayout(rating_)

        # gallery_layout.addRow("Title:", checkbox_layout(self.title_edit))
        # gallery_layout.addRow("Author:", checkbox_layout(self.author_edit))
        # gallery_layout.addRow("Description:", checkbox_layout(self.descr_edit))
        # gallery_layout.addRow("Language:", lang_l)
        # gallery_layout.addRow("Tags:", tags_l)
        # gallery_layout.addRow("Type:", checkbox_layout(self.type_box))
        # gallery_layout.addRow("Status:", checkbox_layout(self.status_box))
        # gallery_layout.addRow("Publication Date:", checkbox_layout(self.pub_edit))
        # gallery_layout.addRow("Path:", self.path_lbl)
        # gallery_layout.addRow("URL:", link_layout)
        
        gallery_layout.addWidget(QLabel("Title:"),                  0, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        gallery_layout.addWidget(QLabel("Author:"),                 1, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        gallery_layout.addWidget(QLabel("Description:"),            2, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        gallery_layout.addWidget(QLabel("Language:"),               3, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        gallery_layout.addWidget(QLabel("Tags:"),                   4, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        gallery_layout.addWidget(QLabel("Type:"),                   5, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        gallery_layout.addWidget(QLabel("Status:"),                 6, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        gallery_layout.addWidget(QLabel("Publication Date:"),       7, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        gallery_layout.addWidget(QLabel("Path:"),                   8, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        gallery_layout.addWidget(QLabel("URL:"),                    9, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        gallery_layout.addLayout(checkbox_layout(self.title_edit),  0, 1)
        gallery_layout.addLayout(checkbox_layout(self.author_edit), 1, 1)
        gallery_layout.addLayout(checkbox_layout(self.descr_edit),  2, 1)
        if isinstance(lang_l, QLayout):
            gallery_layout.addLayout(lang_l,                        3, 1)
        else:
            gallery_layout.addWidget(lang_l,                        3, 1)
        gallery_layout.addLayout(tags_l,                            4, 1)
        gallery_layout.addLayout(checkbox_layout(self.type_box),    5, 1)
        gallery_layout.addLayout(checkbox_layout(self.status_box),  6, 1)
        gallery_layout.addLayout(checkbox_layout(self.pub_edit),    7, 1)
        gallery_layout.addWidget(self.path_lbl,                     8, 1)
        gallery_layout.addLayout(link_layout,                       9, 1)

        gallery_layout.setColumnStretch(0, 0)
        gallery_layout.setColumnStretch(1, 1)

        gallery_layout.setRowStretch(0, 0)
        gallery_layout.setRowStretch(1, 0)
        gallery_layout.setRowStretch(2, 0)
        gallery_layout.setRowStretch(3, 0)
        gallery_layout.setRowStretch(4, 5)
        gallery_layout.setRowStretch(5, 0)
        gallery_layout.setRowStretch(6, 0)
        gallery_layout.setRowStretch(7, 0)
        gallery_layout.setRowStretch(8, 0)
        gallery_layout.setRowStretch(8, 0)

        if not self._multiple_galleries: QWidget.setTabOrder(self.url_edit, self.title_edit)
        QWidget.setTabOrder(self.title_edit, self.author_edit)
        QWidget.setTabOrder(self.author_edit, self.descr_edit)
        QWidget.setTabOrder(self.descr_edit, self.lang_box)
        QWidget.setTabOrder(self.lang_box, self.rating_box)
        QWidget.setTabOrder(self.rating_box, self.tags_edit)
        QWidget.setTabOrder(self.tags_edit, self.type_box)
        QWidget.setTabOrder(self.type_box, self.status_box)
        if not self._multiple_galleries: self.url_btn.setFocusPolicy(Qt.ClickFocus)
        self.link_edit.setFocusPolicy(Qt.ClickFocus)
        self.link_btn.setFocusPolicy(Qt.ClickFocus)
        self.link_btn2.setFocusPolicy(Qt.ClickFocus)
        self.done.setFocusPolicy(Qt.ClickFocus)
        self.cancel.setFocusPolicy(Qt.ClickFocus)
        self.pub_edit.setFocusPolicy(Qt.ClickFocus)
        self.path_lbl.setFocusPolicy(Qt.ClickFocus)

    def url_btn_clicked(self):
        if self.get_metadata_type == 'single':
            self.web_metadata()
        elif self.get_metadata_type == 'all':
            self.parent().gallery_dialog_group.all_metadata()

    # def resizeEvent(self, event):
        # self.tags_edit.setFixedHeight(int(event.size().height()//8))
        # self.descr_edit.setFixedHeight(int(event.size().height()//12.5))
        # print([self.size(), self.scroll_area.verticalScrollBar().isVisible(), self.scroll_area.horizontalScrollBar().isVisible()])
        # print([self.size()])
        # return super().resizeEvent(event)

    def _find_combobox_match(self, combobox, key, default):
        f_index = combobox.findText(key, Qt.MatchFixedString)
        if f_index != -1:
            combobox.setCurrentIndex(f_index)
            return True
        else:
            combobox.setCurrentIndex(default)
            return False

    def setGallery(self, gallery):
        "To be used for when editing a gallery"
        if isinstance(gallery, gallerydb.Gallery):
            self.gallery = gallery

            if not self._multiple_galleries:
                self.url_edit.setText(gallery.link)

            self.title_edit.setText(gallery.title)
            self.author_edit.setText(gallery.artist)
            self.descr_edit.setText(gallery.info)
            self.rating_box.setValue(gallery.rating)

            self.tags_edit.setText(utils.tag_to_string(gallery.tags))


            if not self._find_combobox_match(self.lang_box, gallery.language, 1):
                self._find_combobox_match(self.lang_box, app_constants.G_DEF_LANGUAGE, 1)
            if not self._find_combobox_match(self.type_box, gallery.type, 0):
                self._find_combobox_match(self.type_box, app_constants.G_DEF_TYPE, 0)
            if not self._find_combobox_match(self.status_box, gallery.status, 0):
                self._find_combobox_match(self.status_box, app_constants.G_DEF_STATUS, 0)

            gallery_pub_date = "{}".format(gallery.pub_date).split(' ')
            try:
                self.gallery_time = datetime.strptime(gallery_pub_date[1], '%H:%M:%S').time()
            except IndexError:
                pass
            qdate_pub_date = QDate.fromString(gallery_pub_date[0], "yyyy-MM-dd")
            self.pub_edit.setDate(qdate_pub_date)

            self.link_lbl.setText(gallery.link)
            self.path_lbl.setText(gallery.path)

        elif isinstance(gallery, list):
            g = gallery[0]
            if all(map(lambda x: x.title == g.title, gallery)):
                self.title_edit.setText(g.title)
                self.title_edit.g_check.setChecked(True)
            if all(map(lambda x: x.artist == g.artist, gallery)):
                self.author_edit.setText(g.artist)
                self.author_edit.g_check.setChecked(True)
            if all(map(lambda x: x.info == g.info, gallery)):
                self.descr_edit.setText(g.info)
                self.descr_edit.g_check.setChecked(True)
            if all(map(lambda x: x.tags == g.tags, gallery)):
                self.tags_edit.setText(utils.tag_to_string(g.tags))
                self.tags_edit.g_check.setChecked(True)
            if all(map(lambda x: x.language == g.language, gallery)):
                if not self._find_combobox_match(self.lang_box, g.language, 1):
                    self._find_combobox_match(self.lang_box, app_constants.G_DEF_LANGUAGE, 1)
                self.lang_box.g_check.setChecked(True)
            if all(map(lambda x: x.rating == g.rating, gallery)):
                self.rating_box.setValue(g.rating)
                self.rating_box.g_check.setChecked(True)
            if all(map(lambda x: x.type == g.type, gallery)):
                if not self._find_combobox_match(self.type_box, g.type, 0):
                    self._find_combobox_match(self.type_box, app_constants.G_DEF_TYPE, 0)
                self.type_box.g_check.setChecked(True)
            if all(map(lambda x: x.status == g.status, gallery)):
                if not self._find_combobox_match(self.status_box, g.status, 0):
                    self._find_combobox_match(self.status_box, app_constants.G_DEF_STATUS, 0)
                self.status_box.g_check.setChecked(True)
            if all(map(lambda x: x.pub_date == g.pub_date, gallery)):
                gallery_pub_date = "{}".format(g.pub_date).split(' ')
                try:
                    self.gallery_time = datetime.strptime(gallery_pub_date[1], '%H:%M:%S').time()
                except IndexError:
                    pass
                qdate_pub_date = QDate.fromString(gallery_pub_date[0], "yyyy-MM-dd")
                self.pub_edit.setDate(qdate_pub_date)
                self.pub_edit.g_check.setChecked(True)
            if all(map(lambda x: x.link == g.link, gallery)):
                self.link_lbl.setText(g.link)
                self.link_lbl.g_check.setChecked(True)

    def newUI(self):

        f_local = QGroupBox("Directory/Archive")
        f_local.setCheckable(False)
        self.main_layout.addWidget(f_local)
        local_layout = QHBoxLayout()
        f_local.setLayout(local_layout)

        choose_folder = QPushButton("From Directory")
        choose_folder.clicked.connect(lambda: self.choose_dir('f'))
        local_layout.addWidget(choose_folder)

        choose_archive = QPushButton("From Archive")
        choose_archive.clicked.connect(lambda: self.choose_dir('a'))
        local_layout.addWidget(choose_archive)

        self.file_exists_lbl = QLabel()
        local_layout.addWidget(self.file_exists_lbl)
        self.file_exists_lbl.hide()

    def choose_dir(self, mode):
        """
        Pass which mode to open the folder explorer in:
        'f': directory
        'a': files
        Or pass a predefined path
        """
        self.done.show()
        self.file_exists_lbl.hide()
        if mode == 'a':
            name = QFileDialog.getOpenFileName(self, 'Choose archive', filter=utils.ARCHIVE_FILTER)
            name = name[0]
        elif mode == 'f':
            name = QFileDialog.getExistingDirectory(self, 'Choose folder')
        elif mode:
            if os.path.exists(mode):
                name = mode
            else:
                return None
        if not name:
            return
        head, tail = os.path.split(name)
        name = os.path.join(head, tail)
        parsed = utils.title_parser(tail)
        self.title_edit.setText(parsed['title'])
        self.author_edit.setText(parsed['artist'])
        self.path_lbl.setText(name)
        if not parsed['language']:
            parsed['language'] = app_constants.G_DEF_LANGUAGE
        l_i = self.lang_box.findText(parsed['language'])
        if l_i != -1:
            self.lang_box.setCurrentIndex(l_i)
        if gallerydb.GalleryDB.check_exists(name):
            self.file_exists_lbl.setText('<font color="red">Gallery already exists.</font>')
            self.file_exists_lbl.show()
        # check galleries
        gs = 1
        if name.endswith(utils.ARCHIVE_FILES):
            gs = len(utils.check_archive(name))
        elif os.path.isdir(name):
            g_dirs, g_archs = utils.recursive_gallery_check(name)
            gs = len(g_dirs) + len(g_archs)
        if gs == 0:
            self.file_exists_lbl.setText('<font color="red">Invalid gallery source.</font>')
            self.file_exists_lbl.show()
            self.done.hide()
        if app_constants.SUBFOLDER_AS_GALLERY:
            if gs > 1:
                self.file_exists_lbl.setText('<font color="red">More than one galleries detected in source! Use other methods to add.</font>')
                self.file_exists_lbl.show()
                self.done.hide()

    def check(self):
        if not self._multiple_galleries:
            if len(self.title_edit.text()) == 0:
                self.title_edit.setFocus()
                self.title_edit.setStyleSheet("border-style:outset;border-width:2px;border-color:red;")
                return False
            elif len(self.author_edit.text()) == 0:
                self.author_edit.setText("Unknown")

            if len(self.path_lbl.text()) == 0 or self.path_lbl.text() == 'No path specified':
                self.path_lbl.setStyleSheet("color:red")
                self.path_lbl.setText('No path specified')
                return False
        return True

    def reject(self):
        if self.check():
            msgbox = QMessageBox()
            msgbox.setText("<font color='red'><b>Noo oniichan! You were about to add a new gallery.</b></font>")
            msgbox.setInformativeText("Do you really want to discard?")
            msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msgbox.setDefaultButton(QMessageBox.No)
            if msgbox.exec() == QMessageBox.Yes:
                self.parent().gallery_dialog_group.unregister(self)
                self.delayed_close()
        else:
            self.delayed_close()

    def web_metadata(self, fetch_inst: fetch.Fetch = None):
        if not self.path_lbl.text():
            return
        self.link_lbl.setText(self.url_edit.text())
        self.url_for_metadata = self.url_edit.text()
        self.url_btn.hide()
        self.url_prog.show()

        def status(stat):
            def do_hide():
                try:
                    self.url_prog.hide()
                    self.url_btn.show()
                except RuntimeError:
                    pass

            if stat:
                do_hide()
            else:
                danger = """QProgressBar::chunk {
                    background: QLinearGradient( x1: 0, y1: 0, x2: 1, y2: 0,stop: 0 #FF0350,stop: 0.4999 #FF0020,stop: 0.5 #FF0019,stop: 1 #FF0000 );
                    border-bottom-right-radius: 5px;
                    border-bottom-left-radius: 5px;
                    border: .px solid black;}"""
                self.url_prog.setStyleSheet(danger)
                QTimer.singleShot(3000, do_hide)

        def gallery_picker(gallery, title_url_list, q):
            self.parent()._web_metadata_picker(gallery, title_url_list, q, self)

        try:
            dummy_gallery = self.make_gallery(self.gallery, False)
        except AttributeError:
            dummy_gallery = self.make_gallery(gallerydb.Gallery(), False, True)
        if not dummy_gallery:
            status(False)
            return

        dummy_gallery._g_dialog_url = self.url_edit.text()
        dummy_gallery.new_gallery = self._new_single_gallery
        if isinstance(fetch_inst, fetch.Fetch):
            # Fetch was provided in the call, i.e. from a GalleryDialogGroup
            # GalleryDialogGroup will also start the fetch thread
            fetch_inst.galleries.append(dummy_gallery)
            fetch_inst.GALLERY_PICKER.connect(gallery_picker)
            fetch_inst.GALLERY_EMITTER.connect(self.set_web_metadata)
            fetch_inst.FINISHED.connect(status)
        else:
            # single GalleryDialog metadata fetch
            self._fetch_inst = fetch.Fetch()
            # self._fetch_thread = QThread(self)
            self._fetch_thread = QThread(self.parent())
            self._fetch_thread.setObjectName("GalleryDialog metadata thread")
            self._fetch_inst.moveToThread(self._fetch_thread)
            self._fetch_thread.started.connect(self._fetch_inst.auto_web_metadata)

            self._fetch_inst.galleries = [dummy_gallery]
            self._disconnect(self._fetch_inst)
            self._fetch_inst.GALLERY_PICKER.connect(gallery_picker)
            self._fetch_inst.GALLERY_EMITTER.connect(self.set_web_metadata)
            self._fetch_inst.FINISHED.connect(status)
            self._fetch_thread.start()
            log_i('fetch thread started')
            
    def set_web_metadata(self, metadata):
        assert isinstance(metadata, gallerydb.Gallery)
        log_d(f'got metadata for {metadata.link} ({metadata.title})')
        if metadata.link != self.url_for_metadata: return
        log_d(f'applying metadata for {metadata.link} ({metadata.title})')
        self.link_lbl.setText(metadata.link)
        self.title_edit.setText(metadata.title)
        self.author_edit.setText(metadata.artist)
        # tags = ""
        # lang = ['English', 'Japanese']
        self._find_combobox_match(self.lang_box, metadata.language, 2)
        self.tags_edit.setText(utils.tag_to_string(metadata.tags))
        pub_string = "{}".format(metadata.pub_date)
        pub_date = QDate.fromString(pub_string.split()[0], "yyyy-MM-dd")
        self.pub_edit.setDate(pub_date)
        self._find_combobox_match(self.type_box, metadata.type, 0)

    def make_gallery(self, new_gallery, add_to_model=True, new=False):
        def is_checked(widget):
            return widget.g_check.isChecked()
        if self.check():
            if is_checked(self.title_edit):
                new_gallery.title = self.title_edit.text()
                log_d('Adding gallery title')
            if is_checked(self.author_edit):
                new_gallery.artist = self.author_edit.text()
                log_d('Adding gallery artist')
            if not self._multiple_galleries:
                new_gallery.path = self.path_lbl.text()
                log_d('Adding gallery path')
            if is_checked(self.descr_edit):
                new_gallery.info = self.descr_edit.toPlainText()
                log_d('Adding gallery descr')
            if is_checked(self.type_box):
                new_gallery.type = self.type_box.currentText()
                log_d('Adding gallery type')
            if is_checked(self.lang_box):
                new_gallery.language = self.lang_box.currentText()
                log_d('Adding gallery lang')
            if is_checked(self.rating_box):
                new_gallery.rating = self.rating_box.value()
                log_d('Adding gallery rating')
            if is_checked(self.status_box):
                new_gallery.status = self.status_box.currentText()
                log_d('Adding gallery status')
            if is_checked(self.tags_edit):
                if self.tags_append.isChecked():
                    new_gallery.tags = utils.tag_to_dict(utils.tag_to_string(new_gallery.tags)+","+ self.tags_edit.toPlainText())
                else:
                    new_gallery.tags = utils.tag_to_dict(self.tags_edit.toPlainText())
                log_d('Adding gallery: tagging to dict')
            if is_checked(self.pub_edit):
                qpub_d = self.pub_edit.date().toString("ddMMyyyy")
                dpub_d = datetime.strptime(qpub_d, "%d%m%Y").date()
                try:
                    d_t = self.gallery_time
                except AttributeError:
                    d_t = datetime.now().time().replace(microsecond=0)
                dpub_d = datetime.combine(dpub_d, d_t)
                new_gallery.pub_date = dpub_d
                log_d('Adding gallery pub date')
            if is_checked(self.link_lbl):
                new_gallery.link = self.link_lbl.text()
                log_d('Adding gallery link')

            if new:
                if not new_gallery.chapters:
                    log_d('Starting chapters')
                    thread = threading.Thread(target=utils.make_chapters, args=(new_gallery,))
                    thread.start()
                    thread.join()
                    log_d('Finished chapters')
                    if app_constants.MOVE_IMPORTED_GALLERIES:
                        app_constants.OVERRIDE_MONITOR = True
                        new_gallery.move_gallery()
                if add_to_model:
                    self.parent().default_manga_view.add_gallery(new_gallery, True)
                    log_i('Sent gallery to model')
            else:
                if add_to_model:
                    self.parent().default_manga_view.replace_gallery([new_gallery], False)
            return new_gallery

    def link_set(self):
        t = self.link_edit.text()
        self.link_edit.hide()
        self.link_lbl.show()
        self.link_lbl.setText(t)
        self.link_btn2.hide()
        self.link_btn.show() 

    def link_modify(self):
        t = self.link_lbl.text()
        self.link_lbl.hide()
        self.link_edit.show()
        self.link_edit.setText(t)
        self.link_btn.hide()
        self.link_btn2.show()

    def _disconnect(self, fetch_inst):
        try:
            fetch_inst.GALLERY_PICKER.disconnect()
            fetch_inst.GALLERY_EMITTER.disconnect()
            fetch_inst.FINISHED.disconnect()
        except TypeError:
            pass

    def delayed_close(self):
        self.parent().gallery_dialog_group.unregister(self)
        if isinstance(self._fetch_thread, QThread) and self._fetch_thread.isRunning():
            self._fetch_thread.finished.connect(self.close)
            self.hide()
        else:
            self.close()

    def accept(self):
        self.make_gallery(gallerydb.Gallery(), new=True)
        self.delayed_close()

    def accept_edit(self):
        gallerydb.execute(database.db.DBBase.begin, True)
        app_constants.APPEND_TAGS_GALLERIES = self.tags_append.isChecked()
        settings.set(app_constants.APPEND_TAGS_GALLERIES, 'Application', 'append tags to gallery')
        for g in self._edit_galleries:
            self.make_gallery(g)
        self.delayed_close()
        gallerydb.execute(database.db.DBBase.end, True)

    def reject_edit(self):
        self.delayed_close()

    def keyPressEvent(self, event):
        # Return:
        #   When url_edit is in focus: click url_btn
        #   else when anything but descr_edit or tags_edit is in focus: accept_edit
        # Escape:
        #   reject_edit
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if not self._multiple_galleries and self.url_edit.hasFocus():
                self.url_btn_clicked()
            elif not self.descr_edit.hasFocus() and not self.tags_edit.hasFocus():
                self.done.click()
        elif event.key() == Qt.Key_Escape:
            self.cancel.click()
        elif not self._multiple_galleries and event.key() == Qt.Key_Control:
            self.url_btn.setText("Get all metadata")
            self.get_metadata_type = 'all'
        return super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if not self._multiple_galleries and event.key() == Qt.Key_Control:
            self.url_btn.setText("Get metadata")
            self.get_metadata_type = 'single'
        return super().keyReleaseEvent(event)

    def closeEvent(self, event):
        self.parent().gallery_dialog_group.unregister(self)

    def showEvent(self, a0: QShowEvent) -> None:
        if self.parentWidget():
            parent_rect = QRect(self.parentWidget().mapToGlobal(QPoint(0, 0)), self.parentWidget().size())
            self.move(QStyle.alignedRect(Qt.LayoutDirection.LeftToRight, Qt.AlignmentFlag.AlignCenter, self.size(), parent_rect).topLeft())
            
        if self._multiple_galleries:
            self.tags_edit.setFocus()
        else:
            self.url_edit.setFocus()
        
        return super().showEvent(a0)


class GalleryDialogGroup(QObject):
    """
    Keeps track of open GalleryDialogs.
    Facilitates the fetching of multiple galleries' metadata at once.
    """
    def __init__(self, parent):
        super(GalleryDialogGroup, self).__init__(parent)
        self.gds : set[tuple[GalleryDialog, Any]] = set()
        self.fetch_insts : set[fetch.Fetch] = set()

    def register(self, gd: GalleryDialog, arg: Any | list[Any] = None):
        """
        Add a reference to ``gd`` with its spawn argument (Gallery, list of
        Galleries or file system path).
        """
        if arg is None: return

        if isinstance(arg, (list, tuple)):
            for el in arg:
                self.gds.add((gd, el))
        else:
            self.gds.add((gd, arg))

    def unregister(self, gd: GalleryDialog):
        """
        Remove all registered references to ``gd``.
        """
        for el in self.gds.copy():
            reg_gd, *_ = el
            if gd is reg_gd:
                self.gds.remove(el)

    def remove_fetch(self, fetch_inst):
        """
        Remove a ``fetch.Fetch`` instance if it was active.
        """
        try:
            self.fetch_insts.remove(fetch_inst)
        except KeyError:
            pass

    def get_open_dialog(self, arg: Any) -> GalleryDialog | None:
        """
        Get the open ``GalleryDialog`` that registered itself with ``arg`` or
        ``None`` if no such dialog is registered.
        """
        for (reg_gd, reg_arg) in self.gds:
            if arg == reg_arg:
                return reg_gd
        return None

    def all_metadata(self):
        """
        Make a Fetch instance (and thread) that collects the gallery URLs from
        all registered GalleryDialogs, then start the thread here.

        Make a new Fetch instance and thread when the API limit for a single
        request is reached.
        """
        if len(self.gds) == 0: return

        fetch_inst = None
        fetch_thread = None
        g_counter = 0

        for i, (gd, _) in enumerate(self.gds):
            if i % pewnet.CommonHen._QUEUE_LIMIT == 0:
                if fetch_thread is not None:
                    fetch_thread.start()
                    log_i(f'fetch thread started for {g_counter} galler{"y" if g_counter == 1 else "ies"}')
                    g_counter = 0

                fetch_inst = fetch.Fetch()
                self.fetch_insts.add(fetch_inst)
                fetch_thread = QThread(self.parent())
                fetch_thread.setObjectName("GalleryDialog metadata thread")
                fetch_inst.moveToThread(fetch_thread)
                fetch_inst.FINISHED.connect(lambda: self.remove_fetch(fetch_inst))
                fetch_thread.started.connect(fetch_inst.auto_web_metadata)

            log_d(f'adding url from GalleryDialog {i+1}/{len(self.gds)}')
            gallery = gd.web_metadata(fetch_inst=fetch_inst)
            if gallery is not None: self.gallery_to_dialog[gallery] = gd
            g_counter += 1

        fetch_thread.start()
        log_i(f'fetch thread started for {g_counter} galler{"y" if g_counter == 1 else "ies"}')