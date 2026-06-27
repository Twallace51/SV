# Github notes

## how did I set SVremote?

I’ll check your current Git remote configuration so I can tell you exactly how SVremote was set and the command pattern to reproduce it.

From your current repo config, SVremote is set as a named remote pointing to:

https://github.com/Twallace51/SV.git

So the way you set it was most likely:

git remote add SVremote https://github.com/Twallace51/SV.git

If the remote already existed and you changed it, then it would have been:

git remote set-url SVremote https://github.com/Twallace51/SV.git

Your repo currently has both remotes configured:

SVremote → https://github.com/Twallace51/SV.git
origin → https://github.com/Twallace51/SV
To verify anytime:
git remote -v


## how do I clone SVremote to a new computer?

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
