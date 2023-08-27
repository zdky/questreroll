<p align="center">
    <img width="100%" src="https://i.imgur.com/69PK6tT.png">
</p>
<p align="center">
    <a href="https://www.python.org/downloads/">
        <img src="https://img.shields.io/badge/python-3.11%2B-blue.svg?style=flat-square&logo=python&logoColor=white&color=blue" alt="python 3.11">
    </a>
    <a href="https://github.com/zdky/questreroll/issues">
        <img src="https://img.shields.io/github/issues/zdky/questreroll?style=flat-square" alt="open issues">
    </a>
    <a href="https://github.com/zdky/questreroll/issues?q=is%3Aissue+is%3Aclosed">
        <img src="https://img.shields.io/github/issues-closed/zdky/questreroll?style=flat-square" alt="closed issues">
    </a>
    <a href="https://t.me/Zhidky" target="_blank">
        <img src="https://img.shields.io/badge/Telegram-Join-Blue.svg?style=flat-square&logo=telegram&logoColor=white&color=blue" alt="Telegram">
    </a>
    <a href="https://www.donationalerts.com/r/zhidky" target="_blank">
        <img src="https://img.shields.io/badge/PayPal-Thanks-blue.svg?style=flat-square&logo=paypal&logoColor=fff" alt="Support me">
    </a>
</p>

> ❗️ **Only for those who purchased a Founder's Pack before June 29, 2020**

## Motivation ⚡
> I originally wanted to make a simple bot for daily rewards with notification, but this feature was removed from the game. I got desperate and did nothing, in July i asked to make a replace quest feature from [PRO100KatYT](https://github.com/PRO100KatYT/SaveTheWorldClaimer) and he inspired me. I'm too lazy to open the game every time to get a new quest or replace it,
so I created this bot to do it at any time.<br><br>p.s. *python is my hobby since 2012, I rarely write anything and I'm not sure about the quality of the code. This is my first github project, welcome any bug fixes! :)*

## Features ⚙️

* Auto receipt of a daily quest.
* Quest replace via buttons.
* Rough quest completion time.
* Auth with epic games link to auth-code.
* Auto refresh Fortnite API tokens.
* Filter: first user can use bot / all.
* UX only in 2 message (hi/quest).
* Autodetect telegram user language (compare with FN langs).
* Change quest language (all 15 langs from Fortnite).
* Delete all telegram trash messages.
* Server load info, user bot stats.
* Use .json file for "database".

## Demo 🎬

<p align="center">
    <img width="40%" src="https://github.com/zdky/questreroll/blob/main/res/demo.gif">
</p>


## Getting Started 🚀

<details>
<summary>Expand to see guide for Linux (Ubuntu)</summary>

- **Step 1**: Clone the repository using command:

```bash
git clone https://github.com/zdky/questreroll.git
```

- **Step 2**: Open project folder:

```bash
cd questreroll
```

- **Step 0**: Add your telegram bot token to config.py:

```bash
tg_token = 'YOUR_TOKEN'
```

- **Step 3**: Check your python version:

```bash
python3.11 --version
```

If your version is below 3.11, install python:

```bash
apt install software-properties-common -y
add-apt-repository "ppa:deadsnakes/ppa" -y
apt update && apt install python3.11 python3.11-venv
```

- **Step 4**: Create virtual environment:

```bash
python3.11 -m venv .
```

- **Step 5**: Run virtual environment:

```bash
source bin/activate
```

- **Step 6**: Install requirements:

```bash
pip install -r requirements.txt
```

- **Step 7**: Grant rights:

```bash
chmod +x start.py
```

- **Step 8**: Create service:

```bash
nano /etc/systemd/system/questreroll.service
```

- **Step 9**: Put in file questreroll.service:

```bash
[Unit]
Description=questreroll_bot
After=syslog.target
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/questreroll
ExecStart=/root/questreroll/bin/python3.11 /root/questreroll/start.py
RestartSec=5
Restart=always

[Install]
WantedBy=multi-user.target
```

Save and exit:

```bash
CTRL+O > Enter > CTRL+X
```

- **Step 10**: Start service:

```bash
systemctl enable questreroll.service
systemctl start questreroll.service
```

</details>
<br>
<details>
<summary>Expand to see guide for debug on Linux (Ubuntu)</summary>

- **Debug**: Check status service:

```bash
systemctl status questreroll
```

- **Debug**: Check program logs:

```bash
journalctl -u questreroll.service
```

- **Debug**: Reload service:

```bash
systemctl reload-or-restart questreroll.service
```

- **Stop program**:

```bash
systemctl stop questreroll.service
```
</details>

> *You are a beginner and you can't get your bot to run? [Write me about it!](https://github.com/zdky/questreroll/issues/) I can also add a guide for Windows.*


## Upcoming ⏳
* Add the mod, "auto-replace quest with small V-bucks reward" as well as "replace difficult quests".
* Add notifications when a "new quest appears", as well as "3/3 quests, please complete them"
* Add translation of the entire bot into all fortnite languages.
* Rewrite imports with best practices.

## Community

### Contributing 👨‍💻

Contributions of any kind are very welcome, and would be much appreciated.
For Code of Conduct, see [Contributor Convent](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

To get started, fork the repo, make your changes, add, commit and push the code, then come back here to open a pull request. If you're new to GitHub or open source, [this guide](https://www.freecodecamp.org/news/how-to-make-your-first-pull-request-on-github-3#let-s-make-our-first-pull-request-) or the [git docs](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request) may help you get started, but feel free to reach out if you need any support.

[![Submit a PR](https://img.shields.io/badge/Submit_a_PR-GitHub-%23060606?style=for-the-badge&logo=github&logoColor=fff)](https://github.com/zdky/questreroll/compare)


### Reporting Bugs 🕵

If you've found something that doesn't work as it should, or would like to suggest a new feature, then go ahead and raise a ticket on GitHub.
For bugs, please outline the steps needed to reproduce, and include relevant info like system info and resulting logs.

[![Raise an Issue](https://img.shields.io/badge/Raise_an_Issue-GitHub-%23060606?style=for-the-badge&logo=github&logoColor=fff)](https://github.com/zdky/questreroll/issues/)

### Supporting ☕

[![Sponsor zdky](https://img.shields.io/badge/Sponsor-zdky-%23158c41?style=for-the-badge&logo=paypal&logoColor=fff)](https://www.donationalerts.com/r/zhidky)

### Thanks ❤️

Thanks to everyone on github who writes projects like this, you've taught me a lot.<br>Special thanks to [**PRO100KatYT**](https://github.com/PRO100KatYT/SaveTheWorldClaimer) for the inspiration, and also for the json file with all the quests and fortnite reroll api endpoint.

## License


> _**[zdky/questreroll](https://github.com/zdky/questreroll)** is licensed under [MIT](https://github.com/zdky/questreroll/blob/main/LICENSE) © [zdky](https://t.me/Zhidky) 2023._<br>
> <sup align="right">For information, see <a href="https://tldrlegal.com/license/mit-license">TLDR Legal > MIT</a></sup>

<details>
<summary>Expand License</summary>

```
The MIT License (MIT)
Copyright (c) zdky <dodwop@gmail.com> 

Permission is hereby granted, free of charge, to any person obtaining a copy 
of this software and associated documentation files (the "Software"), to deal 
in the Software without restriction, including without limitation the rights 
to use, copy, modify, merge, publish, distribute, sub-license, and/or sell 
copies of the Software, and to permit persons to whom the Software is furnished 
to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included install 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANT ABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NON INFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

</details>

> **Note:** *Valid auth codes may allow an attacker to compromise your account!*

###### <p align=center>Portions of the materials used are trademarks and/or copyrighted works of Epic Games, Inc.<br>This material is not official and is not endorsed by Epic Games, Inc.<br>All rights reserved by Epic Games, Inc.</p>
