# features

Feature plugins work with the output of a mask and its filter, the binary “state image”.

### [PixelSum](../shapeflow/plugins/PixelSum.py)

The most basic feature: it just calculates the total number of “1” pixels in the state image.

### [Area_mm2](../shapeflow/plugins/Area_mm2.py)

This feature takes the total number of pixels and converts it to an area in mm², taking into account the DPI of the design file. If you keep the  formatted design file in the same dimensions you used to fabricate the chip in the first place, you should get a good approximation of the actual area.

### [Volume_uL](../shapeflow/plugins/Volume_uL.py)

By multiplying the area in mm² by a channel height in mm, this feature estimates the volume in µL.

* `height`: channel height in mm. For chips with channels of different height, you can override this parameter for specific masks to set a different height in those channels.

