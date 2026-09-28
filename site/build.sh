#!/bin/sh
# Builds the static site into dist/ for hosting (Vercel: masar.o-rbit.co).
# index.html is authored without a document wrapper (the Claude artifact host adds one),
# so this adds the wrapper, link-preview tags and a favicon.
set -e
cd "$(dirname "$0")"
rm -rf dist && mkdir -p dist
cp -R assets dist/assets
{
  cat <<'HEAD'
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#F0F0F0">
<link rel="icon" type="image/png" href="/assets/logo-masar-ar.png">
<meta property="og:type" content="website">
<meta property="og:url" content="https://masar.o-rbit.co/">
<meta property="og:title" content="Masar | مسار">
<meta property="og:description" content="Meet the students who are ready to choose. A university roadshow across Egypt and the Gulf by GET ED × Eshra7ly.">
<meta property="og:image" content="https://masar.o-rbit.co/assets/og.jpg">
<meta name="twitter:card" content="summary_large_image">
<style>html{color-scheme:light}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>
</head>
<body>
HEAD
  cat index.html
  printf '\n</body>\n</html>\n'
} > dist/index.html
echo "built dist/"
