The original creator twiddly has halted work on Happypanda in favor of its successor `HappyPanda X <https://github.com/happypandax/server>`__. But I still use this program, so I'll keep making fixes and adding features that I find useful.
==============================================================================================================================================================================================================================================

   Follow twiddly on twitter to keep up to date with HPX:

   .. image:: https://img.shields.io/twitter/follow/pewspew.svg?style=social&label=Follow
     :target: https://twitter.com/twiddly_


What is Happypanda?
===================

A cross-platform manga/doujinshi manager with namespace & tag support.


Features
========

-  Portable, self-contained in folder and cross-platform
-  Low memory footprint
-  Advanced gallery search with regex support (`learn more about it here <https://github.com/Pewpews/happypanda/wiki/Gallery-Searching>`__)
-  Gallery tagging: user-defined namespaces and tags
-  Gallery metadata fetching from the web (supports various sources)
-  Gallery downloading from the web, supporting various sources (Gallery downloading from E-Hentai costs Credits/GP)
-  Folder monitoring that'll notify you of filesystem changes
-  Multiple ways of adding galleries to make it as convienient as possible!
-  Recursive directory/archive scanning
-  Supports ZIP/CBZ, RAR/CBR, 7Z/CB7 and directories with loose files
-  Very customizable
-  And lots more...


Screenshots
===========

.. image:: https://github.com/Pewpews/happypanda/raw/master/misc/screenshot1.png
    :width: 100%
    :align: center

.. image:: https://github.com/Pewpews/happypanda/raw/master/misc/screenshot2.png
    :width: 100%
    :align: center

.. image:: https://github.com/Pewpews/happypanda/raw/master/misc/screenshot3.png
    :width: 100%
    :align: center


How to install and run
======================

Windows
^^^^^^^

#. Download the archive from `releases <https://github.com/Pewpews/happypanda/releases>`__
#. Extract the archive to its own folder
#. Find Happypanda.exe and double click on it!

Mac and Linux
^^^^^^^^^^^^^

Install from PYPI or see `INSTALL.md <https://github.com/Pewpews/happypanda/blob/master/INSTALL.md>`__

PYPI (up to Happypanda v1.1)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``pip install happypanda`` (thanks `@Evolution0 <https://github.com/Evolution0>`__) and then run with ``happypanda --home``

Note: use of the ``--home`` flag will make happypanda create required files and directories at:

On windows: ``'C:\Users\YourName\AppData\Local\Pewpew\Happypanda'``

On mac: ``'/Users/YourName/Library/Application Support/Happypanda'``

On linux: ``'/home/YourName/.local/share/Happypanda'``


Updating
========

| Overwrite your previous installation.
| More info in the `wiki <https://github.com/Pewpews/happypanda/wiki>`__


PYPI
^^^^

``pip install --upgrade happypanda``


Misc.
=====

For general documentation (how to add galleries and usage of the search), check the `wiki <https://github.com/Pewpews/happypanda/wiki>`__.

People wanting to import galleries from the Pururin database torrent should find `this <https://github.com/Exedge/Convertor>`__ useful.


Dependencies
============

-  Qt5 (Install this first) >= 5.4
-  PyQt5 (pip)
-  requests (pip)
-  beautifulsoup4 (pip)
-  watchdog (pip)
-  rarfile (pip)
-  robobrowser (pip)
-  Send2Trash (pip)
-  Pillow (pip) or PIL
-  python-dateutil (pip)
-  QtAwesome (pip)
-  py7zr (pip)


Contributing
============

Please refer to ``HappypandaX`` instead.