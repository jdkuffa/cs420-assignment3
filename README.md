# CS420 Assignment 3: Prompt Engineering For In-Context Learning

# **1. Introduction** 

An analysis of various prompting strategies using two large language models: GPT-4 and Mistral Large. To evaluate the quality of the outputs, a third model (Llama 4 Maverick) is used as a judge, providing comparative assessments and insights into model behavior and performance.

# **2. Getting Started**  

This project is implemented in **Python 3.9+** and is compatible with **macOS, Linux, and Windows**.  

## **2.1 Preparations**  

1. Clone the repository to your workspace:  
```shell
git clone https://github.com/jdkuffa/cs420-assignment3.git
```

2. Navigate into the repository:

```shell
cd cs420-assignment3
```

3. Set up a virtual environment and activate it:

### For macOS/Linux:

```shell
python -m venv ./venv/
```
```shell
source venv/bin/activate
```

### For Windows:

1. Install ```virtualenv```:
```shell
pip install virtualenv
```

2. Create a virtual environment:
```shell
python -m virtualenv venv
```

3. Activate the environment
```shell
venv\Scripts\activate
```

The name of your virtual environment should now appear within parentheses just before your commands.

To deactivate the virtual environment, use the command:

```shell
deactivate
```

## **2.2 Install Packages**

Install the required dependencies:

```shell
pip install -r requirements.txt
```

## **2.3 Run Program**
0. Add GitHub token

Create a file named ```token.txt``` and go to [this link](https://github.com/settings/personal-access-tokens) to make a fine-grained PAT to add to this file.

You can do this manually or from the command line as shown below (feel free to replace ```nano``` with your preferred editor):

```shell
touch token.txt && nano token.txt
```

1. Run ```data_automation.py```

To process the incoming ```data.csv``` file containing prompts and problems.

```python
python3 data_automation.py
```

2. Run ```judge_model.py```

To add a column to the output database containing the judge model's analyses.

```python
python3 judge_model.py
```

3. Run ```evaluation_metrics.py```
   
To add a column to the output database containing the exact match, BLEU, or embedding-based similarity scores.

```python
python3 evaluation_metrics.py
```

# 3. Report

The assignment report is available in the root directory, labelled as "analysis-report.pdf".

# 4. Extra Credit

For the extra credit, we included Llama 4 Maverick 17B 128E Instruct FP8 as a judge model. 

We wrote the ```judge_model.py``` script to output the resulting comparison and analysis from the model to the ```output_db.csv``` under the column "Output Model 3: Meta Llama 4 Maverick." 

The metrics have also been added to the analyses sections of the report.
