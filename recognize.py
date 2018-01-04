import numpy as np
import cv2
import imutils
from sklearn.metrics import pairwise
import time
import subprocess
import thread

# global variables
bg = None

#-------------------------------------------------------------------------------
# Function - To find the running average over the background
#-------------------------------------------------------------------------------
def run_avg(image, accumWeight):
    global bg
    # initialize the background
    if bg is None:
        bg = image.copy().astype("float")
        return

    # compute weighted average, accumulate it and update the background
    cv2.accumulateWeighted(image, bg, accumWeight)

#-------------------------------------------------------------------------------
# Function - To segment the region of hand in the image
#-------------------------------------------------------------------------------
def segment(image, threshold=25):
    global bg
    # find the absolute difference between background and current frame
    diff = cv2.absdiff(bg.astype("uint8"), image)

    # threshold the diff image so that we get the foreground
    thresholded = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)[1]

    # get the contours in the thresholded image
    (_, cnts, _) = cv2.findContours(thresholded.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # return None, if no contours detected
    if len(cnts) == 0:
        return
    else:
        # based on contour area, get the maximum contour which is the hand
        segmented = max(cnts, key=cv2.contourArea)
        return (thresholded, segmented)

#-------------------------------------------------------------------------------
# Function - To count the number of fingers in the segmented hand region
#-------------------------------------------------------------------------------
def count(thresholded, segmented):
	# find the convex hull of the segmented hand region
	chull = cv2.convexHull(segmented)

	# find the most extreme points in the convex hull
	extreme_top    = tuple(chull[chull[:, :, 1].argmin()][0])
	extreme_bottom = tuple(chull[chull[:, :, 1].argmax()][0])
	extreme_left   = tuple(chull[chull[:, :, 0].argmin()][0])
	extreme_right  = tuple(chull[chull[:, :, 0].argmax()][0])

	# find the center of the palm
	cX = (extreme_left[0] + extreme_right[0]) / 2
	cY = (extreme_top[1] + extreme_bottom[1]) / 2

	# find the maximum euclidean distance between the center of the palm
	# and the most extreme points of the convex hull
	distance = pairwise.euclidean_distances([(cX, cY)], Y=[extreme_left, extreme_right, extreme_top, extreme_bottom])[0]
	maximum_distance = distance[distance.argmax()]
	
	# calculate the radius of the circle with 80% of the max euclidean distance obtained
	radius = int(0.8 * maximum_distance)
	
	# find the circumference of the circle
	circumference = (2 * np.pi * radius)

	# take out the circular region of interest which has 
	# the palm and the fingers
	circular_roi = np.zeros(thresholded.shape[:2], dtype="uint8")
	
	# draw the circular ROI
	cv2.circle(circular_roi, (cX, cY), radius, 255, 1)
	
	# take bit-wise AND between thresholded hand using the circular ROI as the mask
	# which gives the cuts obtained using mask on the thresholded hand image
	circular_roi = cv2.bitwise_and(thresholded, thresholded, mask=circular_roi)

	# compute the contours in the circular ROI
	(_, cnts, _) = cv2.findContours(circular_roi.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

	# initalize the finger count
	count = 0

	# loop through the contours found
	for c in cnts:
		# compute the bounding box of the contour
		(x, y, w, h) = cv2.boundingRect(c)

		# increment the count of fingers only if -
		# 1. The contour region is not the wrist (bottom area)
		# 2. The number of points along the contour does not exceed
		#     25% of the circumference of the circular ROI
		if ((cY + (cY * 0.25)) > (y + h)) and ((circumference * 0.25) > c.shape[0]):
			count += 1

	return count


def reset():
    global status
    print 'reset before'
    time.sleep(5.5)
    print 'reset after'
    status = 0

def reset_forward():
    global status
    print 'reset before'
    time.sleep(20.5)
    print 'reset after'
    status = 0


#-------------------------------------------------------------------------------
# Main function
#-------------------------------------------------------------------------------
if __name__ == "__main__":
    # initialize accumulated weight
    accumWeight = 0.5

    # get the reference to the webcam
    camera = cv2.VideoCapture(0)

    # region of interest (ROI) coordinates
    top, right, bottom, left = 10, 350, 225, 590

    # initialize num of frames
    num_frames = 0

    # calibration indicator
    calibrated = False

    global status
    status = 0 ## 0 for idle, ready for reciving cmd, 1 for busy

    # keep looping, until interrupted
    while(True):
        # get the current frame
        (grabbed, frame) = camera.read()

        # resize the frame
        frame = imutils.resize(frame, width=700)

        # flip the frame so that it is not the mirror view
        frame = cv2.flip(frame, 1)

        # clone the frame
        clone = frame.copy()

        # get the height and width of the frame
        (height, width) = frame.shape[:2]

        # get the ROI
        roi = frame[top:bottom, right:left]

        # convert the roi to grayscale and blur it
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (7, 7), 0)

        # to get the background, keep looking till a threshold is reached
        # so that our weighted average model gets calibrated
        if num_frames < 30:
            run_avg(gray, accumWeight)
            if num_frames == 1:
            	print "[STATUS] please wait! calibrating..."
            elif num_frames == 29:
				print "[STATUS] calibration successfull..."       
        else:
            # segment the hand region
            hand = segment(gray)

            # check whether hand region is segmented
            if hand is not None:
                # if yes, unpack the thresholded image and
                # segmented region
                (thresholded, segmented) = hand

                # draw the segmented region and display the frame
                cv2.drawContours(clone, [segmented + (right, top)], -1, (0, 0, 255))

                # count the number of fingers
                fingers = count(thresholded, segmented)

                if status == 0:
                    if fingers == 2:
                        p = subprocess.Popen('rosrun turtle_move line', stdout=subprocess.PIPE, shell=True)
                        print('line')
                        # time.sleep(5)
                        # p.kill()
                        thread.start_new_thread(reset, ())
                    elif fingers == 1:
                        p = subprocess.Popen('rosrun turtle_move circle', stdout=subprocess.PIPE, shell=True)
                        print 'circle'
                        # time.sleep(5)
                        # p.kill()
                        thread.start_new_thread(reset, ())
                    elif fingers == 3:
                        p = subprocess.Popen('rosrun turtle_move move_turtle_goforward', stdout=subprocess.PIPE, shell=True)
                        print 'goforward'
                        # time.sleep(5)
                        # p.kill()
                        thread.start_new_thread(reset, ())
                    thread.start_new_thread(reset_forward, ())
                    status = 1

                cv2.putText(clone, str(fingers), (70, 45), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
                
                # show the thresholded image
                cv2.imshow("Thesholded", thresholded)

        # draw the segmented hand
        cv2.rectangle(clone, (left, top), (right, bottom), (0,255,0), 2)

        # increment the number of frames
        num_frames += 1

        # display the frame with segmented hand
        cv2.imshow("Video Feed", clone)

        # observe the keypress by the user
        keypress = cv2.waitKey(1) & 0xFF

        # if the user pressed "q", then stop looping
        if keypress == ord("q"):
            break

# free up memory
camera.release()
cv2.destroyAllWindows()
