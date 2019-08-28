import sys
from os import path
from cx_Freeze import setup, Executable



here = path.abspath(path.dirname(__file__))

filespath = sys.path
filespath.append(path.join(here,"version"))

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {"packages": [],
					 "path": filespath,
					 "excludes": ["tkinter", "numpy", "test"],
					 "include_files" : [("res", "res")]}

bdist_msi_options = {
					'upgrade_code' : '{45FF1AC3-FE88-49D9-9BC9-47F43E7844F6}',
					'install_icon' : 'happypanda.ico'}

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == "win32":
    base = "Win32GUI"


exe = Executable("version\\main.py",
				 base=base,
				 targetName="Happypanda.exe",
				 icon="happypanda.ico",
				 shortcutName='Happypanda',
				 shortcutDir='ProgramMenuFolder')

setup(  name='Happypanda',
		version='1.2',
		description='A cross platform manga/doujinshi manager with namespace & tag support',
		long_description=open('README.rst').read(),
		url='https://github.com/Pewpews/happypanda',
		author='Pewpew',
		author_email='pew@pewpew.moe',
		license='GPLv2+',
		classifiers=[
			'Development Status :: 5 - Production/Stable',
			'Intended Audience :: End Users/Desktop',
			'Topic :: Database :: Front-Ends',
			'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
			'Programming Language :: Python :: 3',
			'Programming Language :: Python :: 3.4',
			'Programming Language :: Python :: 3.5',
			'Programming Language :: Python :: 3.6',
		],
		keywords=['manga', 'doujinshi', 'downloader', 'management', 'cross-platform'],
		include_package_data=True,
		package_data={
			'': ['res/*'],
			'res': ['*'],
		},
        options = {"build_exe": build_exe_options, "bdist_msi" : bdist_msi_options},
        executables = [exe])