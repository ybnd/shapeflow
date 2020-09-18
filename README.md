# shapeflow

[![travis-ci](https://travis-ci.org/ybnd/isimple.svg?branch=master)](https://travis-ci.org/ybnd/isimple)
[![codecov](https://codecov.io/gh/ybnd/isimple/branch/master/graph/badge.svg)](https://codecov.io/gh/ybnd/isimple)

|| [Installation](#Installation-and-usage) | [Tutorial](docs/tutorial.md) | [Troubleshooting](docs/troubleshooting.md) | [Related literature](#Related-literature) ||

A tool for extracting time-series data from video footage of microfluidic devices with complex channel geometry.

<div align="center"><img src="https://i.postimg.cc/xTMZzYnj/abstract5-720x540.gif" width="600px"/></div>

By providing quantitative insight into the flow dynamics of self-powered microfluidic systems, shapeflow supports research involving the [SIMPLE platform](https://www.biw.kuleuven.be/biosyst/mebios/biosensors-group/research-topics/Microfluidics_folder/simple-platform). 

This software is developed in collaboration with the [KULeuven Biosensors lab](https://twitter.com/KULBiosensors).

<div align="center"><img src="https://i.postimg.cc/W3qF15rK/demo-final-30fps-600x400.gif" width="600px"/></div>

### Installation and usage

1. Install [Python 3.7+](https://www.python.org/downloads/) and [git](https://git-scm.com/downloads), if you haven’t yet. On Windows, **select the option ‘Add Python to PATH’!**
2. Make a new folder in a convenient location
3. [Download a deployment script](https://github.com/ybnd/shapeflow/releases/download/0.3.20-test/deploy_isimple-0.3.20-test.py) and save it to that folder
4. Run the deployment script.
5. Once the installation is done, you can start the application by running `app.py`. A new browser window or tab should open for the user interface.

* A tutorial: [docs/tutorial.md](docs/tutorial.md)

* To resolve common issues: [docs/troubleshooting.md](docs/troubleshooting.md)

### Development

* About the Python library: [docs/shapeflow.md](docs/shapeflow.md)

* Generating deployment scripts [docs/deployment.md](docs/deployment.md)

* Setting up the development environment for the user interface: [ui/README.md](ui/README.md)

### Related literature

* [Self-powered Imbibing Microfluidic Pump by Liquid Encapsulation: SIMPLE](https://doi.org/10.1039/C4LC00920G)
  Tadej Kokalj, Younggeun Park, Matjaž Vencelj, Monika Jenko, and Luke P Lee. *Lab on a Chip*, **2014**. 
  
* [Self-powered infusion microfluidic pump for ex vivo drug delivery](https://doi.org/10.1007/s10544-018-0289-1)
  Francesco Dal Dosso, Tadej Kokalj, Jaroslav Belotserkovsky, Dragana Spasic and Jeroen Lammertyn. *Biomedical Microdevices*, **2018**

* [Innovative Hydrophobic Valve Allows Complex Liquid Manipulations in a Self-Powered Channel-Based Microfluidic Device](https://doi.org/10.1021/acssensors.8b01555)
  Francesco Dal Dosso, Lisa Tripodi, Dragana Spasic, Tadej Kokalj, and Jeroen Lammertyn. *ACS Sensors*, **2019**

### Acknowledgements

The chips in the introduction and demo videos were designed and manufactured by Francesco Dal Dosso, Henry Ordutowski and Lorenz van Hilleghem.

### License

As of now, an appropriate license for this repository has not been determined yet. All rights are held by KU Leuven.
