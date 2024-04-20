#!/bin/bash

#SBATCH --job-name=moska_simulate
#SBATCH --account=project_2009838
#SBATCH --time=00:15:00
#SBATCH --partition=test
#SBATCH --output=moska_simulate_%j.out
#SBATCH --error=moska_simulate_%j.err
#SBATCH --mail-type=END

# Reserve compute
#SBATCH --cpus-per-task=40
#SBATCH --nodes=2
#SBATCH --ntasks=2
#SBATCH --mem-per-cpu=4G
# Print all arguments
echo "All arguments: $@"

module purge
module load tensorflow/2.15

RLF_MOSKA_SCRATCH="/scratch/project_2009838/Moska"

PIP_EXE=./venv/bin/pip3
PYTHON_EXE=./venv/bin/python3

if [ ! -d ./venv ]; then
    python3 -m venv venv
    source ./venv/bin/activate
    $PIP_EXE install --upgrade pip
    $PIP_EXE install --extra-index-url https://pypi.nvidia.com tensorrt-bindings==8.6.1 tensorrt-libs==8.6.1 tensorflow[and-cuda]==2.15
    $PIP_EXE install -e ./RLFramework
fi

source ./venv/bin/activate

which python3
which pip3
nvidia-smi

PYTHON_EXE=./venv/bin/python3

# Show information about the environment:
$PYTHON_EXE -c "import tensorflow as tf; print(tf.__version__)"
$PYTHON_EXE -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
$PYTHON_EXE --version

DATA_FOLDER=$RLF_MOSKA_SCRATCH/TestData
MODEL_FOLDER=$RLF_MOSKA_SCRATCH/TestModels

rm -r $DATA_FOLDER

mkdir -p $DATA_FOLDER
mkdir -p $MODEL_FOLDER

for node in $(scontrol show hostname $SLURM_JOB_NODELIST); do

    new_data_folder=$DATA_FOLDER"/"$node
    echo $new_data_folder

    if [ -d $new_data_folder ]; then
        rm -r $new_data_folder
    fi

    srun --nodes=1 --ntasks=1 --cpus-per-task=40 -w $node $PYTHON_EXE ./Moska/only_simulate.py \
    --folder=$new_data_folder \
    --model_base_folder=$MODEL_FOLDER \
    --num_games=1050 \
    --num_cpus=35 \
    --num_files=350 &
done
wait