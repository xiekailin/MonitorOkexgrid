# OKX网格监控与工具脚本

## 项目简介
本项目包含两个主要脚本：
- `Okgrid.py`：用于监控OKX现货网格策略收益，并通过Bark推送通知。
- `getOkcelue.py`：用于查询当前运行中的OKX网格策略ID等信息。

## 环境依赖
- Python 3.6 及以上
- 依赖库：
  - requests
  - python-dotenv

安装依赖：
```bash
pip3 install requests python-dotenv
```

## 环境变量配置
请在项目根目录下新建 `.env` 文件，内容如下（用你自己的信息替换）：
```
API_KEY=你的APIKEY
SECRET_KEY=你的SECRETKEY
PASSPHRASE=你的PASSPHRASE
BARK_DEVICE_KEY=你的BARKKEY
ALGO_ID=你的ALGOID
```
> `.env` 文件已被加入 `.gitignore`，不会上传到代码仓库。

## 运行方法
### 1. 查询网格策略ID
```bash
python3 getOkcelue.py
```
根据输出找到你需要监控的 `algoId`，填入 `.env` 文件。

### 2. 启动监控脚本
```bash
python3 Okgrid.py
```
或后台运行并输出日志：
```bash
cd /home/OkMontio && pkill -f "python Okgrid.py" ; sleep 1 ; nohup python3 Okgrid.py >> okgrid.log 2>&1 &
```

### 3. 查看日志
```bash
tail -f okgrid.log
```

## 代理设置（如需科学上网）
如果服务器需要代理访问OKX，可在运行前设置环境变量：
```bash
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
```

## 常见问题
- `.env` 文件一定不要上传到代码仓库！
- 云服务器需能正常访问 https://www.okx.com，否则脚本无法获取数据。
- 建议API权限最小化，不要开通提币权限。
- Bark推送需提前在手机端配置好。

如有其他问题，欢迎随时提问！ 