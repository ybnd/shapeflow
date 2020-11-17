# filters

Filter plugins operate on a mask and are meant to filter out the liquid of interest in that mask. This filtered portion is returned as a binary image, and can be seen in the “state image” on the filter page.

### [HsvRangeFilter](../shapeflow/plugins/HsvRangeFilter.py)

The basic filter, it works by filtering out all colors *around* the center color you select on the filter page. Its configuration consists of

* `range`: the range around the color, in **H**ue, **S**aturation and **V**alue. The default setting of (10,75,75) works well for most cases, but if you find that the filter misses some regions, you can try increasing the range. Mixing or separating colors can be handled by increasing the **H** range (allowing more hues through) and uneven lighting/shadows can be compensated for by increasing the **V** ranges (lightness of the color)
* `color`: the center color. While just clicking within a mask on the filter page is easier, you can also set this to a specific color.
* `close`: kernel size (circular) of a [morphological closing operation](https://en.wikipedia.org/wiki/Closing_(morphology)). Optional; if `close` is set to 0, no closing will be performed. You may want to configure a higher opening kernel size if you notice that the state image of the corresponding frame includes noise (small objects or colored pixels) outside of its main area.
* `open`: kernel size (circular) of a [morphological opening operation](https://en.wikipedia.org/wiki/Opening_(morphology)). 
Optional; if `open` is set to 0, no opening will be performed. 

You may want to configure a higher closing kernel size if you notice that the state image of the corresponding frame includes noise (small ‘holes’ or non-colored pixels) inside of its main area.

### [BackgroundFilter](BackgroundFilter.py)

This filter works in exactly the same way as the [HsvRangeFilter](# HsvRangeFilter), but inverts its binary image at the very end. Therefore, you should configure its center color to the color of the background of the channel. Because of this, the BackgroundFilter may perform better in cases where the foreground consists of multiple colors (e.g. chromatographic separation in porous materials) or when you want to measure liquids of any color that’s not background (e.g. multiple liquid plugs pass through the same channel).

