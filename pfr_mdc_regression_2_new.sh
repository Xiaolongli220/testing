#!/bin/bash
echo "===============Step: pfr_mdc_regresson==============="
if [ $# == 0 ]; then
    echo "Wrong usage: pfr_mdc_regression.sh unique_id private(true|false) interop(true|false) mail test_framework(pyats|tcl) input_configuration pi25(true|false) delete_topology(true|false) job_type archive(true|false) hub_branch transit_hub_branch branch1_branch branch2_branch [branches]"
    exit 1
fi

unique_id=$1
shift
private=$1
shift
interop=$1
shift
mail=$1
shift
test_framework=$1
shift
input_configuration=$1
shift
pi25=$1
shift
dt=$1
shift
job=$1
shift
archive=$1
shift
if [ "$job" = "idc" -o "$job" = "mhop" -o "$job" = "pd_idc_mhop" -o "$job" = "dca" -o "$job" = "dca2" -o "$job" = "site_manager" -o "$job" = "teacat" ];then
job_params=$1
shift
else
job_params=","
fi

if [ "$job" = "dca" -o "$job" = "dca2" -o "$job" = "site_manager" -o "$job" = "teacat" ];then
tbcreate=$1
shift
unique_testbed=$1
shift
else
tbcreate='true'
unique_testbed='false'
fi

echo "Interop $interop, Private $private"
if [ "$interop" = "true" ]; then
    hb=$1
    shift
    thb=$1
    shift
    b1=$1
    shift
    b2=$1
    shift
else
    hb=$1
    shift
    thb=$hb
    b1=$hb
    b2=$hb
fi

if [ "$private" = "false" ];then
    branch="$@"
fi


#cd /ws/rchaowdh-sjc/test_harness/
#source /opt/pyats_share/env_jialpeng.sh
source /opt/pyats_5.0/env_jialpeng.sh
export PYTHONUNBUFFERED=1
#cd /storage/users/dich/tcl_script/PI_pfrv3
echo "This script is in location `pwd`"
RECIPIENTS="$mail@cisco.com"
#d=`date +'%m-%d-%Y'`
d=`date +"%m-%d-%Y-%H-%M-%S"`
output="pfr_mdc_$d"
echo "dich debug"
echo "Private:" $private
echo "Email:" $mail
echo "Job:" $job
echo "Archive:" $archive
echo "Test_Framework:" $test_framework
echo "Input_Conguration:" $input_configuration
echo "PI25:" $pi25
echo "Unique_id:" $unique_id
echo "DeleteTopology:" $dt
echo "job_params: " $job_params
echo "tbcreate:" $tbcreate
echo "unique_testbed:" $unique_testbed






if [ "$hb" = "/home/cisco/image/latest" ];then
echo "===============Step: get latest image from 10.74.28.11//home/cisco/image/ ==============="
no_proxy=localhost,127.0.0.0,127.0.1.1,127.0.1.1,local.home,10.74.28.11
echo "$(env | grep no_proxy)"
wget -nd -N ftp://cisco:cisco@10.74.28.11//home/cisco/image/
#sleep 10
image=`grep -o '>csr1000v-universalk9.BLD_POLARIS_DEV_LATEST.*serial.ova'  ./index.html |tail -n -1|grep -o csr.*ova`
image1="/home/cisco/image/$image"
hb=$image1
thb=$image1
b1=$image1
b2=$image1
fi

echo "HUB:" $hb
echo "Transite_Hub:" $thb
echo "Branch1:" $b1
echo "Branch2:" $b2
#python copy_latest_polaris.py -b $hb $thb $b1 $b2
#qiangwa modi
#python os_play.py -p $private -m $mail -j $job -a $archive -tf $test_framework -ic $input_configuration -pi $pi25 -ui $unique_id -deleteTopology $dt -hb $hb -thb $thb -b1 $b1 -b2 $b2 > $output.txt
if [ "$job" = "idc" -o "$job" = "mhop" -o "$job" = "pd_idc_mhop" -o "$job" = "dca" -o "$job" = "dca2" -o "$job" = "site_manager" -o "$job" = "teacat" ];then
env | grep PYTHON
echo "===============Step: Run with job_params==============="
python os_play_new.py -p $private -m $mail -j $job -a $archive -tf $test_framework -ic $input_configuration -pi $pi25 -ui $unique_id -deleteTopology $dt -hb $hb -thb $thb -b1 $b1 -b2 $b2 -tbCreateFlag $tbcreate -job_params $job_params -unique_testbed $unique_testbed 
else
echo "===============Step: Run without job_params==============="
python os_play_new.py -p $private -m $mail -j $job -a $archive -tf $test_framework -ic $input_configuration -pi $pi25 -ui $unique_id -deleteTopology $dt -hb $hb -thb $thb -b1 $b1 -b2 $b2 -unique_testbed $unique_testbed
fi


#python os_play.py -p $private -m $mail -j $job -a $archive -tf $test_framework -ic $input_configuration -pi $pi25 -ui $unique_id -deleteTopology $dt -hb $hb -thb $thb -b1 $b1 -b2 $b2

#chmod 777 $output.txt
#op=`cat $output.txt`
#echo $d
#echo "$op"
#TITLE="[$d]Nightly regression report for PM_PI"
#echo $TITLE
#echo -e "$op" | mail -s "$TITLE" $RECIPIENTS
#rm $output.txt
