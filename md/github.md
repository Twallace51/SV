# how to clone SVremote to a new computer

On the new computer, do this in order:

Install Git and Python

Install Git for Windows

Install Python 3.14 (or the version you currently use)

Choose a folder and clone

Open PowerShell

Go to where you want the project:
cd E:\SendasVida

Clone from your remote URL:
git clone https://github.com/<your-user-or-org>/SVremote.git SV-1.5

Enter project:
cd SV-1.5

Create and activate virtual environment

Create venv:
py -m venv .venv

Activate it:
..venv\Scripts\Activate.ps1

Install dependencies

pip install -r requirements.txt

Run the app

python __main__.py

Verify remote is correct

git remote -v
