import RPi.GPIO as GPIO
import boto3
import cv2
from PIL import Image
import io
import time
import os
import argparse
import numpy as np
import sys
from threading import Thread
import importlib.util
from botocore.exceptions import ClientError

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(18,GPIO.OUT)

s3 = boto3.client('s3',aws_access_key_id='AWS_ACCESS_KEY_ID', #create s3 client
                      aws_secret_access_key='AWS_SECRET_ACCESS_KEY_ID',
                      region_name='us-east-1')
rekog = boto3.client('rekognition',                               #create rekognition client
                         aws_access_key_id='AWS_ACCESS_KEY_ID',
                         aws_secret_access_key='AWS_SECRET_ACCESS_KEY_ID',
                         region_name='us-east-1'
                    )
ses = boto3.client('ses',aws_access_key_id='AWS_ACCESS_KEY_ID',# create ses client
                      aws_secret_access_key='AWS_SECRET_ACCESS_KEY_ID',
                      region_name='us-east-1')
i =0
def capture():
    global i
    cv2.imwrite("test%s.jpg"%i,frame)#take a snapshot of the frame
    upload('test%s.jpg'%i)
    time.sleep(1)
    email(i)
    i+=1
    
def upload(file_name):#Upload image to S3
    # S3 file name is the same as local file
    object_name = file_name
    #Public S3 bucket in use
    bucket='notification-rpi'
    try:
        response = s3.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def email(number):# Send email to customer by SES
    
    SENDER = "khuongkhoadk1999@gmail.com" #sender's email (company emails in most cases)
    RECIPIENT = "bukhonnhat001@gmail.com" #customer's email
    # The subject line for the email.
    SUBJECT = "Raspberry Pi Security Notification"
    BODY_HTML = """<html>
    <head></head>
    <body>
    <h1>Raspberry Pi Security Notification</h1>
    <p>This email was sent with
    <a href='https://aws.amazon.com/ses/'>Amazon SES</a> using the
    <a href='https://aws.amazon.com/sdk-for-python/'>
      AWS SDK for Python (Boto)</a>.</p>
      <h2>Someone just entered your house</h2>
      <img src="https://notification-rpi.s3.amazonaws.com/test{number}.jpg" >
    </body>
    </html>
            """.format(number=number)
    # The character encoding for the email.
    CHARSET = "UTF-8"
    BODY_TEXT = ("Amazon SES Test (Python)\r\n"
             "This email was sent with Amazon SES using the "
             "AWS SDK for Python (Boto)."
            )
    # Try to send the email.
    try:
    #Provide the contents of the email.
        response = ses.send_email(
            Destination={
            'ToAddresses': [
                RECIPIENT,
                           ],
                        },
            Message={
                'Body': {
                     'Html': {
                         'Charset': CHARSET,
                         'Data': BODY_HTML,
                             },
                     'Text': {
                         'Charset': CHARSET,
                         'Data': BODY_TEXT,
                             }
                        },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                           },
                    },
            Source=SENDER,
        )
# Display an error if something goes wrong.	
    except ClientError as e:
          print(e.response['Error']['Message'])
    else:
          print("Email sent! Message ID:"),
          print(response['MessageId'])
cur_frame = 0
success = True
# Initialize frame rate calculation
frame_rate_calc = 1
freq = cv2.getTickFrequency()
frame_skip = 10 # analyze every 100 frames to cut down on Rekognition API calls

# Initialize video stream
cap = cv2.VideoCapture(0)
if (cap.isOpened()== False): 
        print("Error opening video stream or file")
pause_counter=0
pause=0
time.sleep(1)
counter =0 
while (cap.isOpened()):
    # Start timer (for calculating frame rate)
    t1 = cv2.getTickCount()
    
    ret,frame = cap.read() # get next frame from video

    if cur_frame % frame_skip == 0: # only analyze every n frames
        print('frame: {}'.format(cur_frame)) 

        pil_img = Image.fromarray(frame) # convert opencv frame (with type()==numpy) into PIL Image
        stream = io.BytesIO()
        pil_img.save(stream, format='JPEG') # convert PIL Image to Bytes
        bin_img = stream.getvalue()
        try:
            response = rekog.search_faces_by_image(CollectionId='myCollection', Image={'Bytes': bin_img}, MaxFaces=1, FaceMatchThreshold=85) # call Rekognition
            if response['FaceMatches']: # 
                for face in response['FaceMatches']:
                    print('Hello, ',face['Face']['ExternalImageId'])
                    print('Similarity: ',face['Similarity'])
                    counter +=1 

                
            else:
                 print('No faces matched')  
                 
        except:print('No face detected')  
        
        if counter >= 10:
              print('send email') 
              capture()        
              pause=1
              counter=0
        if pause==1:
             print('DOOR OPEN')
             GPIO.output(18,GPIO.HIGH)
             pause_counter+=1
             
        if pause_counter >20:
              print('DOOR CLOSE')
              GPIO.output(18,GPIO.LOW)
              pause_counter=0
              pause =0
    # Draw framerate in corner of frame
    cv2.putText(frame,'FPS: {0:.2f}'.format(frame_rate_calc),(30,50),cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,0),2,cv2.LINE_AA)
    cv2.imshow('Object detector', frame)
    # Calculate framerate
    t2 = cv2.getTickCount()
    time1 = (t2-t1)/freq
    frame_rate_calc= 1/time1
    #print('counter',counter)
    #print('pause',pause)
    #print('pause_counter',pause_counter)
    if cv2.waitKey(1) == ord('q'):
        break
    cur_frame += 1
# Clean up
cv2.destroyAllWindows()
videostream.stop()