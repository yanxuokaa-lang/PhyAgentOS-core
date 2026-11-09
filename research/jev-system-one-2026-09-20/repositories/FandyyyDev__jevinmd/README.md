
</p>
<h1 align="center">Jevin Md</h1>

<h1 align="center">Jangan lupa kasih stars & follow</h1>

>
>
>
</div>

## Install for termux

```bash
> termux-setup-storage
> pkg update && pkg upgrade
> pkg install git
> pkg install nodejs
> pkg install bash
> pkg install ffmpeg
> pkg install libwebp
> git clone  https://github.com/rdculous/jevinmd
> cd jevinmd
> npm i
> node .

## untuk Sdcard (File yang Sudah Di Download)
> cd /sdcard
> cp -r jevinmd $HOME
> cd jevinmd
> npm i
> node .
```

## Run On Heroku

Simple WhatsApp Bot

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/rdculous/jevinmd)

## UNTUK PENGGUNA RAILWAY

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https%3A%2F%2Fgithub.com%rdculous%jevinmd)

# Get Session [session.data.json] 

[![Run on Repl.it(for get Sessions )](https://repl.it/badge/github/quiec/whatsAlfa)](https://github.com/BOTCAHX/Session-Md)

## FOR OKTETO

* Okteto [`Click Here go to website`](https://okteto.com)

```bash
Login with your github
Click Launch Dev Environment
Choose your repo
```
## UNTUK PENGGUNA WINDOWS/VPS/RDP

* Unduh & Instal Git [`Klik Disini`](https://git-scm.com/downloads)
* Unduh & Instal NodeJS [`Klik Disini`](https://nodejs.org/en/download)
* Unduh & Instal FFmpeg [`Klik Disini`](https://ffmpeg.org/download.html) (**Jangan Lupa Tambahkan FFmpeg ke variabel lingkungan PATH**)
* Unduh & Instal ImageMagick [`Klik Disini`](https://imagemagick.org/script/download.php)

```bash
git clone https://github.com/rdculous/jevinmd
cd jevin
npm i
npm start
```
# Heroku Buildpack
### Instal Buildpack
* heroku/nodejs
* https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git
* https://github.com/DuckyTeam/heroku-buildpack-imagemagick.git


# Hargai Kami Dengan Menambahkan Kredit

---------


## Arguments `node . [--options] [<session name>]` 

### `--session <nama file>`

menggunakan session dari nama file yang berbeda, default `session.data.json`

contoh nama file `raxcel.json` maka penggunaannya `node . --session 'raxcel'`

### `--prefix <prefix>`

* `prefixes` dipisahkan oleh masing-masing karakter
Setel awalan

### `--server`

Digunakan untuk [heroku](https://heroku.com/) atau pindai melalui situs web

### `--db <json-server-url>`

menggunakan db eksternal alih-alih db lokal, **disarankan** menggunakan mongodb

contoh server dengan mongodb `mongodb+srv://<username>:<password>@name-of-your-db.thhce.mongodb.net/myFirstDatabase?retryWrites=true&w=majority`

contoh server dengan repl `https://json-server.nurutomo.repl.co/`

kode: `https://repl.it/@Nurutomo/json-server`

`node . --db 'https://json-server.nurutomo.repl.co/'`

server harus memiliki spesifikasi seperti ini

#### GET

```http
GET /
Accept: application/json
```

#### POST

```http
POST /
Content-Type: application/json

{
 data: {}
}
```

### `--big-qr`

Jika qr unicode kecil tidak mendukung

### `--img`

Aktifkan pemeriksa gambar melalui terminal

### `--test`

**Development** Testing Mode

### `--trace`

```js
conn.logger.level = 'trace'
```

### `--debug`

```js
conn.logger.level = 'debug'
```
#### Thanks To 
**Allah SWT**,

**Orang Tua**,

**All Team Bot Discussion**,

**Semua yang selalu mendukung**


##### Special Thanks to
[![Nurutomo](https://github.com/Nurutomo.png?size=100)](https://github.com/Nurutomo)
[![BochilGaming](https://github.com/BochilGaming.png?size=100)](https://github.com/BochilGaming)
[![adiwajshing/Baileys](https://github.com/adiwajshing.png?size=100)](https://github.com/adiwajshing)
[![BOTCAHX](https://github.com/BOTCAHX.png?size=100)](https://github.com/BOTCAHX)

#### Pengembang Ulang
[![Rdculous](https://github.com/rdculous.png?size=100)](https://github.com/rdculous)
