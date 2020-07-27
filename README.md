# SNP Simple Reader

This is a program that takes a raw genetic data file (provided by [23andMe](https://www.23andme.com/)) and gathers health information from [SNPedia](https://www.snpedia.com/) relevant to your genome.


## Installation
A minimum of Python 3.7 is recommended for maximum compatibility.

Use the package manager  [pip](https://pip.pypa.io/en/stable/)  to install this program's dependencies:

```bash
pip install Pandas
pip install PySide2
pip install BS4
pip install Requests
```

## Usage

**Getting Started:**

1. [Obtain your raw genetic data from 23andMe.](https://customercare.23andme.com/hc/en-us/articles/212196868-Accessing-Your-Raw-Genetic-Data)
2. Click **Load...** on the bottom left of the window to load your raw genetic data file.
3. Give your dataset a name and click **Confirm** to continue.
4. Give the program some time to download data from SNPedia. (**Note:** This will take a few hours.)

**Reading Your Data:**
1. Select your newly created data file from the list menu on the left of the window.
2. Choose your filter criteria and input a search query and/or click **Search** to display your results.
3. Your results will be displayed and broken down by SNP, Repute, and Magnitude.  
4. To display more details about a specific SNP, use select the drop down arrow to display its summary and references (if applicable). 
