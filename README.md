## Inkscape extension to convert SVG document to MP4-animation

Works with Inkscape v.1.2*

\* — *(There's an [issue](https://gitlab.com/inkscape/inkscape/-/issues/2473) on some OSes
with missing `cssselect` Python module, on which Inkscape extensions subsystem depends. 
Manual installation fixes the problem. It may be named `python3-cssselect` 
or just `python-cssselect` in your distro repository.)*

### Description

<img src="https://raw.githubusercontent.com/anonymou8/inkscape-animation/main/screenshot.png" />

Each layer in a document represents a single frame. Bottom layer is the first frame.

If a layer name is one of `bg`, `fg`, `show`, `nohide`, `backgroud` or `foreground` then it 
will be visible throughout animation, and if name is one of `hide`, `hidden`, `scratch`, `temp` 
or`guides` then it will always be hidden.

The extension is of Export type. To use it go to `File → Save As...` or `File → Save a Copy...`
(preferred) and select `Layers as animation frames (ffmpeg) (*.mp4)` for the format.

The extension uses `ffmpeg` to combine PNG images of layers to MP4 file.
User is able to select rendering resolution, framerate and encoding quality (CRF). 
`Loops` parameter tells ffmpeg how many times to repeat a frame sequence. The codec used is h264.

`Set layer opacity to 100%` is useful when you use layer's opacity for onioin skinning, 
then the option will set opacity of each layer to 100% during export.

`Treat first level objects as frames` option tells the extension to make frames from
objects themselves and not layers. Only direct children of a layer can be frames. This
is useful for [quick animations](https://raw.githubusercontent.com/anonymou8/inkscape-animation/main/quick.gif) 
on a single layer. E.g. you can interpolate subpaths with LPE, convert it regular path, 
then break it apart and use the extension without dealing with layers.

<!-- <img src="https://raw.githubusercontent.com/anonymou8/inkscape-animation/main/quick.gif" /> -->

There is an option that allows to save each frame in PNG format to a specified directory. Files will
be named in four-digit format, like `0000.png`, `0001.png` e.t.c. User can change first image number.
Directory will be created if doesn't exist.

### Installation

You must have [ffmpeg](https://ffmpeg.org/) executable installed. Make sure a path to it is 
mentioned in the system global `PATH` variable. As newer version of Inkscape is bundled with 
Python 3, you don't have to worry about the interpreter.

Copy `layers2anim.inx` and `layers2anim.py` to extensions directory (or to its subdirectory) 
and restart Inkscape. You can find out the path to extensions directory in 
`Edit → Preferences → System: User extensions`.

### Example animation 

<img src="https://raw.githubusercontent.com/anonymou8/inkscape-animation/main/swan.gif" />

This GIF was made out of PNGs exported by the extension with these commands:

```
ffmpeg -i %04d.png -vf palettegen=max_colors=256 palette.png
ffmpeg -r 18 -i %04d.png -i palette.png -lavfi paletteuse=bayer:4 swan.gif
```
