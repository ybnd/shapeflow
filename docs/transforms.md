# transforms

Transform plugins compute a transformation matrix from the ROI coordinates (in video frame coordinated) to the corresponding corners of the design (in design coordinates). The flip and rotation operations are handled separately, and applied to the ROI coordinates before computing the transformation matrix.

They also handle coordinate transformation from design coordinates to video coordinates when determining the color of a desgin coordinate (i.e. when configuring a filter by clicking inside a mask on the filter page).

### [PerspectiveTransform](../shapeflow/plugins/PerspectiveTransform.py)

This transform plugin wraps OpenCV’s [`getPerspectiveTransform`](https://docs.opencv.org/2.4.13.7/modules/imgproc/doc/geometric_transformations.html?highlight=getperspectivetransform#getperspectivetransform) function to estimate the transformation matrix and [`warpPerspective`](https://docs.opencv.org/2.4.13.7/modules/imgproc/doc/geometric_transformations.html?highlight=getperspectivetransform#warpperspective) to apply it to a video frame or a coordinate.

