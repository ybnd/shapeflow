"""
    Try-out ORB feature matching for transform estimation
        -> Match features between overlay and video frame
        -> Filter down to best matches (ratio test is sufficient?)
        -> Estimate transformation on set of 'coupled' points

    Notes:
        * Edge detection on iSIMPLE video is not great, probably very dependent on lighting
        * Feature keypoint POSITIONS seem to correspond better, but are probably lighting-dependent as well
        * Could be useful to perform a strict local contrast threshold to even out lighting & color?
        * Naive implementation of ratio test is extremely slow.

!!!!    * Keypoint matches appear to be more or less random...  !!!!

        * Should think about optimizing transform matrix for UNMATCHED points? Is this even a realistic problem?

        * Maybe play around with other keypoint detection & matching schemes...
"""

import itertools as itt
import os
from copy import copy

import cv2
import matplotlib.pyplot as plt
from OnionSVG import OnionSVG

plt.close('all')
os.chdir("/home/ybnd/code/SIMPLE/isimple-video")

def invert(img):
    return cv2.bitwise_not(img)

total_pts = 1000000
best_pts = 100


# Render masks
OnionSVG(
    os.path.join(os.getcwd(), "shuttle_overlay_edges.svg"),
    dpi = 400,
).peel('all', to = "render")

# Load overlay (grayscale)
overlay = cv2.cvtColor(
    cv2.imread(os.path.join(os.getcwd(), "render/overlay.png")),
    cv2.COLOR_BGR2GRAY
)
# Rotate slightly to try to get more interesting features (lame)
""" https://docs.opencv.org/3.0-beta/doc/py_tutorials/py_imgproc/py_geometric_transformations/py_geometric_transformations.html """
rows,cols = overlay.shape
M = cv2.getRotationMatrix2D((cols/2,rows/2),5,1)
overlay = cv2.warpAffine(overlay,M,(cols,rows))

fig_overlay = plt.figure()
plt.imshow(overlay)
plt.title('Overlay')

# Load video frame (grayscale)
cap = cv2.VideoCapture(os.path.join(os.getcwd(), "shuttle_overlay.mp4"))

frameN = cap.get(cv2.CAP_PROP_FRAME_COUNT)
cap.set(cv2.CAP_PROP_POS_FRAMES, int(frameN/8))

ret, frame = cap.read()
frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
frame = cv2.equalizeHist(frame)

fig_frame = plt.figure()
plt.imshow(frame)
plt.title('Frame')

""" https://docs.opencv.org/3.1.0/da/d22/tutorial_py_canny.html """
# Canny edges on frame
edges = invert(cv2.Canny(frame, 100, 150, L2gradient=True, apertureSize=3))
fig_edges = plt.figure()
plt.imshow(edges)
plt.title('Canny edges of Frame')

""" https://docs.opencv.org/3.0-beta/doc/py_tutorials/py_feature2d/py_orb/py_orb.html """
# Start ORB
orb = cv2.ORB_create(nfeatures = total_pts, scoreType=cv2.ORB_FAST_SCORE, WTA_K=4)

### Find keypoints & compute descriptors for overlay
kpt1, dsc1 = orb.detectAndCompute(overlay, None)

kpt1_x = []
kpt1_y = []
for kp in kpt1:
    kpt1_x.append(kp.pt[0])
    kpt1_y.append(kp.pt[1])

plt.figure(fig_overlay.number)
plt.scatter(kpt1_x, kpt1_y)
plt.title('ORB keypoints of overlay')


### Find keypoints & compute descriptors for frame
kpt2, dsc2 = orb.detectAndCompute(frame, None)

kpt2_x = []
kpt2_y = []
for kp in kpt2:
    kpt2_x.append(kp.pt[0])
    kpt2_y.append(kp.pt[1])

plt.figure(fig_frame.number)
plt.scatter(kpt2_x, kpt2_y)
plt.title('ORB keypoints of frame')


### Find keypoints & compute descriptors for edges
kpt3, dsc3 = orb.detectAndCompute(edges, None)

kpt3_x = []
kpt3_y = []
for kp in kpt3:
    kpt3_x.append(kp.pt[0])
    kpt3_y.append(kp.pt[1])

plt.figure(fig_edges.number)
plt.scatter(kpt3_x, kpt3_y)
plt.title('ORB keypoints of edges')



# Start BF Matcher
bf = cv2.BFMatcher_create(cv2.NORM_HAMMING2, crossCheck=True)

# Define ratio test
def ratio_test(matches, ratio = 0.75):
    """https://docs.opencv.org/3.0-beta/doc/py_tutorials/py_feature2d/py_matcher/py_matcher.html"""
    good = []
    for m,n in itt.combinations(matches,2):
        if m.distance < ratio*n.distance:
            good.append(m)
    return good

### Find kpt matches between overlay and frame
matches_frame = sorted(bf.match(dsc2, dsc1), key = lambda x:x.distance)[:best_pts]

img_matches_frame = copy(overlay)
img_matches_frame = cv2.drawMatches(overlay, kpt1, frame, kpt2, matches_frame, img_matches_frame, flags = 2)

plt.figure()
plt.imshow(img_matches_frame)
plt.title('Matches between overlay and frame')

pts_from = []
pts_to = []
for match in matches_frame:
    print(f"Match: [{match.trainIdx}/{len(kpt1)}:{match.queryIdx}/{len(kpt2)}]")
    try:
        pts_from.append(kpt1[match.trainIdx-1])
        pts_to.append(kpt2[match.queryIdx-1])
    except IndexError:
        print(f"\t --> Index error.")

plt.figure()
plt.scatter(kpt1_x, kpt1_y)
plt.scatter(kpt2_x, kpt2_y)
for pt1,pt2 in zip(pts_from, pts_to):
    plt.plot([pt1.pt[0],pt2.pt[0]], [pt1.pt[1],pt2.pt[1]], color = (0,0,0), alpha = 0.1)
plt.title('Matches between overlay and frame')



### Find kpt matches between overlay and edges
matches_edges = sorted(bf.match(dsc3, dsc1), key = lambda x:x.distance)[:best_pts]

img_matches_edges = copy(overlay)
img_matches_edges = cv2.drawMatches(overlay, kpt1, edges, kpt3, matches_frame, img_matches_edges, flags = 2)

plt.figure()
plt.imshow(img_matches_edges)
plt.title('Matches between overlay and edges')

pts_from = []
pts_to = []
for match in matches_edges:
    print(f"Match: [{match.trainIdx}/{len(kpt1)}:{match.queryIdx}/{len(kpt3)}]")
    try:
        pts_from.append(kpt1[match.trainIdx-1])
        pts_to.append(kpt3[match.queryIdx-1])
    except IndexError:
        print(f"\t --> Index error.")

plt.figure()
plt.scatter(kpt1_x, kpt1_y)
plt.scatter(kpt3_x, kpt3_y)
for pt1,pt2 in zip(pts_from, pts_to):
    plt.plot([pt1.pt[0],pt2.pt[0]], [pt1.pt[1],pt2.pt[1]], color = (0,0,0), alpha = 0.1)
plt.title('Matches between overlay and edges')

# Show everything
plt.show()