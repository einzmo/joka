# create_test_video.py
import cv2
import numpy as np

# Create a simple 1-second test video
fps = 30
duration = 1
width, height = 320, 240

out = cv2.VideoWriter('test_video.mp4', cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

for i in range(fps * duration):
    # Create a frame with a moving rectangle
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    x = int((i / (fps * duration)) * width)
    cv2.rectangle(frame, (x, 0), (x + 50, height), (0, 255, 0), -1)
    out.write(frame)

out.release()
print("✅ Created test_video.mp4")