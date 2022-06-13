# SSH to EC2 instance on AWS Business account
ssh -i /Users/niranjan/Documents/code/niranjan-531318808478-useast-1.pem ec2-user@ec2-23-22-56-197.compute-1.amazonaws.com

#Sync folder between EC2 instance on AWS Business account and local
rsync --progress --partial -avz /Users/niranjan/Documents/code/pension/pension_ec2 -e "ssh -i /Users/niranjan/Documents/code/niranjan-531318808478-useast-1.pem" ec2-user@ec2-23-22-56-197.compute-1.amazonaws.com:/home/ec2-user/

#Run Flask app in background
nohup python3 pension-translator.py &

#Kill flask app running in background
pgrep python3
sudo kill <process-id>