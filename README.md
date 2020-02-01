# KUL Biosensors team - iSIMPLE

>**CURRENTLY, THIS REPOSITORY IS PUBLIC, BUT MAYBE IT SHOULDN'T BE**

### Contents

* [isimple/video](isimple/video): Automated video analysis

### Installation

1. Install [Python 3](https://www.python.org/downloads/)
   
* Make sure to **enable** the option "add Python to path"
   
2. Install `git` from the KUL Software center or from [git-scm.com](https://git-scm.com/downloads) (just use all of the default settings in the installer)

3. Clone this repository
   1. Open Command Prompt
   2. Navigate to the folder where you want to put this repository: `cd ...`
   3. Execute  `git clone https://github.com/ybnd/isimple` 
   4. A folder named `isimple` should appear

4. Install the required packages: 

   1.Navigate to the newly created `isimple` folder: `cd isimple`

   2.Execute `pip install --upgrade -r requirements.txt`

   

* This project uses the `cairo` library to render .svg images. The easiest way to install this library for Windows is as follows:
  1. Make sure you have administrator privileges on your computer
  2. Download the `cairo` binaries from [preshing/cairo-windows](https://github.com/preshing/cairo-windows/releases/download/1.15.12/cairo-windows-1.15.12.zip)
  3. Extract the .zip file
  4. Copy `lib/x64/cairo.dll` to `C:\Windows\System32` and `lib/x86/cairo.dll` to `C:\Windows\SysWOW64`

### General usage

To just use the contents of this repository, make sure the `master` branch is checked out. This is by default, and you can double check it by navigating to `isimple` in Command Prompt and executing `git branch`.

Upon import, the [isimple](isimple/__init__.py) package will check if it's being run from the master branch, and pull the latest updates. 
In this way you won't have to worry about staying up to date.

If something breaks because of an update, please harass the person(s) responsible for this repository, since that means that they broke something.

### Contributing

If you intend to contribute, please do so on a separate branch. 
Make sure that you don't push broken code to the master branch, as master commits will be automatically pulled. Once you do, make sure you add any new requirements to [requirements.txt](requirements.txt).

For questions & comments, please contact me.

### Licensing

As of now, an appropriate license for this repository has not been determined yet. All rights are held by KU Leuven.
