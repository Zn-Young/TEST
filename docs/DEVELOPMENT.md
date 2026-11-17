# Git 版本管理与后续修改

本仓库远程地址：https://github.com/Zn-Young/TEST 。以下命令在 PowerShell 项目根目录执行。

## 查看当前状态

~~~powershell
cd D:/Code/Fcode
git status
git remote -v
git log --oneline -5
~~~

工作区是正在编辑的文件；git add 将改动选入下一次提交；git commit 创建本地历史；git push 才上传到 GitHub。保存文件不会自动提交或上传。

## 日常保存修改

先确认 status 和 diff 只包含本次需要保存的内容：

~~~powershell
git status
git diff
git add calib.py calibration_settings.yaml README.md docs
git diff --cached
git commit -m "适配单 USB 双摄采集"
git push
~~~

第一次推送一个新分支时使用 git push -u origin 分支名。尚未提交的文件不会随 push 上传。

若某项路径不存在，git add 会失败，应按本次实际修改的文件名调整。也可以在检查 status 后使用 git add -A，但这会包含所有未忽略的新增、修改和删除。

## 在分支中实现单 USB 适配

先保证当前改动已经提交，再执行：

~~~powershell
git switch main
git pull --ff-only
git switch -c feature/single-usb-stereo
~~~

修改、验证、提交后：

~~~powershell
git push -u origin feature/single-usb-stereo
~~~

在 GitHub 为该分支创建 Pull Request，确认采集、角点筛选、标定和文档符合预期后再合并。合并后，本地 main 可通过 git switch main 和 git pull --ff-only 更新；未合并的功能仍保留在功能分支上。

## 给稳定版本命名

先用 git log 找到希望标记的提交，再创建标签：

~~~powershell
git tag -a baseline-before-single-usb -m "单 USB 双摄改造前的基线"
git push origin baseline-before-single-usb
~~~

如果标签已存在，不要用同名强制覆盖；换一个更明确的版本名称。标签不会自动随着普通 git push 上传。

## 查看或取出历史文件

查看某次提交的 Python 文件：

~~~powershell
git show 提交编号:calib.py
~~~

在当前目录恢复某个文件前，先保存当前改动，然后执行：

~~~powershell
git restore --source=提交编号 -- calib.py calibration_settings.yaml
git diff
~~~

这会覆盖指定文件的未提交内容，恢复后仍需 commit 和 push 才能成为新的远程版本。若只是想比较旧版本，可用独立目录检出，不覆盖当前工作：

~~~powershell
git worktree add --detach ../Fcode-baseline 提交编号
~~~

## 多电脑或多个 Agent 协作

开始工作前先确认工作区状态，在干净工作区执行 git pull --ff-only。避免两位 Agent 同时改同一份工作目录；可使用独立分支、克隆或 worktree。

push 被拒绝时不要 force。先确认远程新增提交，保留本地工作后再合并或 rebase。需要提供 GitHub 身份验证时，使用 Git Credential Manager 的正常登录流程，不要将令牌写入脚本、README 或远程地址。

本地提交身份可按需要仅为本仓库设置：

~~~powershell
git config user.name "你的名称"
git config user.email "你的 GitHub 提交邮箱"
~~~

## 哪些数据不会默认上传

.gitignore 排除 __pycache__、虚拟环境、frames、frames_pair、camera_parameters 等生成目录。board 中已有的标定板 SVG/PNG 则会保留。

如需保存实验数据，应另建有明确名称的归档目录并说明相机、尺寸、单位、采集日期和对应代码提交；不要为了上传实验数据直接删除整个 .gitignore。

开发时更新 README、配置说明及已验证状态，尤其要区分“实现完成”和“真实相机验证通过”。

