#!/bin/bash

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
source /opt/pyats_share/env.sh
cd /storage/users/dich/tcl_script/PI_pfrv3
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
echo "HUB:" $hb
echo "Transite_Hub:" $thb
echo "Branch1:" $b1
echo "Branch2:" $b2


#python copy_latest_polaris.py -b $hb $thb $b1 $b2
#qiangwa modi
#python os_play.py -p $private -m $mail -j $job -a $archive -tf $test_framework -ic $input_configuration -pi $pi25 -ui $unique_id -deleteTopology $dt -hb $hb -thb $thb -b1 $b1 -b2 $b2 > $output.txt
python os_play.py -p $private -m $mail -j $job -a $archive -tf $test_framework -ic $input_configuration -pi $pi25 -ui $unique_id -deleteTopology $dt -hb $hb -thb $thb -b1 $b1 -b2 $b2 

#python os_play.py -p $private -m $mail -j $job -a $archive -tf $test_framework -ic $input_configuration -pi $pi25 -ui $unique_id -deleteTopology $dt -hb $hb -thb $thb -b1 $b1 -b2 $b2

#chmod 777 $output.txt
#op=`cat $output.txt`
#echo $d
#echo "$op"
#TITLE="[$d]Nightly regression report for PM_PI"
#echo $TITLE
#echo -e "$op" | mail -s "$TITLE" $RECIPIENTS
#rm $output.txt
