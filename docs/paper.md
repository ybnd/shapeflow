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

During the global COVID-19 pandemic the ever-growing need for easier, faster, more precise and more compact diagnostic testing has been painfully clear. Microfluidics is a key technology in enabling the minuaturization and automation required to address this. As microfluidic devices have gained a foothold in the field, the limitations of this technology at the point-of-care (POC) have also become clear: all too often, the ideal of a “lab-on-a-chip” (LOC) is not feasible for complex bioassays, and in the extreme such a device kan become more akin to a “chip-in-a-lab”. One of the approaches to mitigate this issue is to replace external, powered propulsion systems (such as syringe pumps) with internal, passive alternatives **REFERENCE**. 

One of the major avenues in self-powered pumping involves leveraging the imbibition of liquids into porous materials such as paper for propulsion. Such paper-based microfludic devices have been developed for a variety of applications ranging from simple single-step lateral flow assays **REFERENCE** to complex multi-step assays **REFERENCE**. However, flowing sample fluidcs through a porous materials necessitates larger volumes, which  is often problematic in a POC context **REFERENCE**. With the (i)SIMPLE platform, we combine the principles of channel-based microfluidics with the self-powered pumping of paper-based microfluidics. By separating propulsion and sample handling in different channels and thus providing more flexibility in terms of the assay.

Variability of pumping performance is a well-documented fact in paper-based microfluidics **REFERENCE**, and even more so when the paper is encapsulated into a chip. This concern highlights the need for smart chip design, which we addressed in a past publication **REFERENCE**. To further facilitate fast prototyping with the (i)SIMPLE platform and support this smart design approach, a fast and convenient way to evaluate an individual chip’s peformance is necessary. Given the geometrical complexity of (i)SIMPLE chips, peforming video analyses on a case-to-case basis is difficult and tedious. We developed `shapeflow` as a solution to this problem.



# Overview

