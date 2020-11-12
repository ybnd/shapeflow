---
title: 'shapeflow: A tool for extracting time-series data from video footage of self-powered microfluidic devices'
tags:
  - microfluidics
  - point-of-care
  - self-powered
  - Python
  - OpenCV
authors:
  - name: Bondarenko Yura
    orcid: 0000-0003-0872-7098
    affiliation: 2
  - name: Francesco Dal Dosso
    orcid: 0000-0003-4546-5154
    affiliation: 1
affiliations:
 - name: Biosensors group, BIOSYST-MeBioS, KU Leuven
   index: 1
 - name: Independent Researcher
   index: 2
date: 4 November 2020
bibliography: paper.bib
---

# Statement of need

During the global COVID-19 pandemic the ever-growing need for easier, faster, more precise and more compact diagnostic testing has been very clear. 
Microfluidics is a key technology in enabling the minuaturization and automation required to address this.
As microfluidic devices have gained a foothold in the field, the limitations of this technology at the point-of-care (POC) have also become clear: all too often, the ideal of a “lab-on-a-chip” (LOC) is not feasible for complex bioassays, and in the extreme such a device kan become more akin to a “chip-in-a-lab”. 
One of the approaches to mitigate this issue is to replace external, powered propulsion systems (such as syringe pumps) with internal, passive alternatives [@Mohammed:2015].

One of the major avenues in self-powered pumping involves leveraging the imbibition of liquids into porous materials such as paper for propulsion. 
Such paper-based microfludic devices have been developed for a variety of applications ranging from simple single-step lateral flow assays [@Eltzov:2015] to multi-step and multiplexed assays [@Martinez:2010]. 
However, due to sample retention in porous materials, the volumes required for a more complex assay are larger than in a channel-based microfluidic device, which can be problematic in a POC context. 
With the (i)SIMPLE platform, we combine the principles of channel-based microfluidics with the self-powered pumping of paper-based microfluidics to separate propulsion and sample handling in different channels, thus providing more flexibility in terms of the assay [@Kokalj:2014]  [@DalDosso:2018].

Variability of pumping performance is a well-documented fact in paper-based microfluidics [@Hu:2014], and even more so when the paper is encapsulated into a chip. 
This concern highlights the need for smart chip design, which we addressed in a past publication [@DalDosso:2019]. 
To further facilitate fast prototyping with the (i)SIMPLE platform and support this smart design approach, a fast and convenient way to evaluate an individual chip’s peformance is necessary. 
Given the geometrical complexity of (i)SIMPLE chips, peforming video analyses on a case-by-case basis is difficult and tedious. We developed `shapeflow` as a solution to this problem. 

# Overview

In order to produce our microfluidics with enough repeatability, we make use of computer-aided design (CAD) software to design the channel geometry for each chip.
The fiinal designs are then used to manufacture chips using CNC and laser cutter equipment (WHICH EQUIPMENT). 
While different fabrication methods will use different computer-aided manufacturing (CAM) techniques (such as lithography or 3D printing), in any case the design of a microfluidic chip represents its ground-truth geometry. 
Furthermore, in order to fabricate chips correctly, the design must match the actual dimensions of the chip it should produce. 

In our image analysis pipeline, we relate the physical chip as recorded in video footage to the actual geometry and dimensions encoded in its design.
We do this by aligning the design to the video footage and estimating a transformation matrix from 'video coordinates' to 'design coordinates'. 
Because the original design of the chip often contains information that is not required for this (such as designs for multiple layers or different materials), we use a 'analysis design' based on the original 'fabrication design' for this step.
The 'analysis design' should include a general outline of the chip to aid alignment along with a number of regions of interest (ROI) to divide the chip into clear parts, such as different channels or different parts of a single channel.
Currently, the application handles 'analysis designs' in SVG format, with each region of interest in a separate layer for ease of processing. Detailed instructions on how to set up these 'analysis designs' are provided in the `shapeflow` repository.

In each ROI, we want to capture one or multiple liquid plugs over the duration of the video. We achieve this by configuring a filter to binarize this plug. 
This has to be repeated for all ROIs in the design. 
The actual data we extract are feature values computed from the resulting binary images. 
A basic example of such a feature is the area of the liquid plug in “real life” units, which we estimate based on the number of pixels in the binary image and the DPI of the design.

In an analysis, any number of features may be requested, and additional parameters can be configured depending on the type of the feature. 
Before starting the analysis, we select a number of frames according to the desired temporal resolution. 
We align the ‘analysis design’ to the video footage and configure the filters for each ROI. 
At this point we can start the analysis. 
For every requested frame in the video, the transformation estimated in the alignment step is first applied to map the frame to 'design coordinates'. 
Then, each ROI in the design is masked off individually, its filter is applied and all requested features are computed based on the resulting binary image.
The resulting values are exported as a time-series spreadsheet for futher processing.

<a flowchart for the preparation-analysis pipeline>

# Application

> * The application is structured as a frontend (user interface) and a backend server which can handle multiple analyses at the same time. 
> * Backend <with a diagram maybe but not really necessary>
>   * REST API (abridged, reference to in-depth version)
>   * Analyses are associated with an ID which is used by the API
>     * This ID is volatile
>   * Video frames are cached, which enables quick re-analysis in case e.g. the user wants to make quick adjustments
>   * Plugin system to easily add functionality
>     * Transformations
>     * Filters
>     * Features
>   * Analysis configuration and results are stored in a SQLite database
>     * Enables undo/redo functionality
>     * Enables selective exporting of results for further processing
>     * Enables easier meta-analyses which will be useful in e.g. characterizing the repeatablity of our data analysis approach
>     * The database also keeps track of video and design files by their hash. This is useful in case files are moved or renamed
>   * Configuration is exported alongside the results for posterity
> * Frontend <with some screenshots>
>   * The user can queue up multiple analyses and configure them separately
>   * Each analysis can be addressed individually through its configure, align, filter and results pages
>   * Preparation is non-linear; the user can skip between different pages in the application in any way they choose
>   * The user can start the analysis queue after preparing multiple analyses to let them run sequentially

# Examples

> add examples from previous Biosensors publications; compare previous manual / ImageJ results to shapeflow
>
> * Original SIMPLE paper (or skip it if design files are not available…)
> * Francesco’s iSIMPLE paper (ask Francesco for the design files)
> * SIMPLE in Theory (select from examples from own archive)
> * Some other recent publication? Something flashy/complex would be nice.
>
> <graphs>
>
> 	* original measurements
> 	* a fill ~ a couple of shapeflow measurements, which should match the thing more or less
>
> </graphs>

# Further work

> * This principle is applicable to paper microfluidics in general and could be useful with complex shapes (give some examples)
> * As of now, we don’t have a solid quantitative insight into the expected variability yet (apart from the regular design-chip mismatch, movements, lighting issues and video quantization error, the expected error sources are inconsistencies in manual layout and filter settings)
> * Currently, the application is run locally by each user; this is something that could pose issues when scaling. Some basic stress testing has shown that the application in its current state is able to handle more than a regular user would need it to. The REST backend is already a good start to transition to a cloud-hosted deployment in case this should prove necessary.
> * The deployment mechanism used is not suited for larger teams and may be replaced in the future should this prove necessary. For the current team size and the current maintainers this system is easy to use and support.
> * Support other design file formats and make formatting design files more straightforward
>   * In our research we use .svg files for designs, which are easy to format
>   * For now, other file formats could be used if they’re converted to .svg first (e.g. more conventional CAD formats such as .dxf)
>   * Most of these formats should be relatively easy to convert using Inkscape (also FOSS)
>   * We use Inkscape for lal of our design work, and developing a plugin to simplify the formatting of design files for use with shapeflow could be interesting to consider for future efforts.
> * Support multiple formats for exporting results
>   * Our team mainly uses Excel for other data analysis, so this is the go-to in our case
>   * We use pandas for result handling, so it will be easy to add support for other formats such as .csv, .json or databases.



> Should also include the .meta files & results in docs/paper as supplementary info and also host the video files somewhere other than the actual repository.



<!--- Reference DOI added to render citations as links. Should be removed when submitting. --->

[@Mohammed:2015]: https://doi.org/10.1016/j.protcy.2015.07.010
[@Martinez:2010]: https://doi.org/10.1021/ac9013989
[@Eltzov:2015]: https://doi.org/10.1002/elan.201500237
[@Kokalj:2014]: https://doi.org/10.1039/C4LC00920G
[@DalDosso:2018]: https://doi.org/10.1007/s10544-018-0289-1
[@DalDosso:2019]: https://doi.org/10.1016/j.sna.2019.01.005
[@Hu:2014]: https://doi.org/10.1016/j.bios.2013.10.075
