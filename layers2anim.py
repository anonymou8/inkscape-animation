import sys, os, subprocess, tempfile
from itertools import filterfalse
from shutil import copyfile
import inkex
from inkex.base import (
    InkscapeExtension, TempDirMixin,
    SvgInputMixin, SvgOutputMixin
)
from inkex.command import inkscape

Mixins = (SvgInputMixin, SvgOutputMixin, TempDirMixin)
class Layers2Anim(*Mixins, InkscapeExtension):
    def add_arguments(self, pars):
        pars.add_argument('--firstlev', type=inkex.Boolean, default=False)
        pars.add_argument('--scale', type=float, default=100)
        pars.add_argument('--fps', type=float, default=12)
        pars.add_argument('--loops', type=int, default=1)
        pars.add_argument('--backandforth', type=inkex.Boolean, default=False)
        
        pars.add_argument('--opac', type=inkex.Boolean, default=True)
        pars.add_argument('--tran', type=inkex.Boolean, default=False)
        pars.add_argument('--rsvg', type=inkex.Boolean, default=True)
        
        pars.add_argument('--codec', type=str, default='mp4')
        pars.add_argument('--crf',  type=int, default=23)
        
        pars.add_argument('--path', type=str, default='')
        pars.add_argument('--pngn', type=int, default=0)
        pars.add_argument('--ffplay', type=inkex.Boolean, default=False)
        
        pars.add_argument('--tab') # not used

    def effect(self):
        opts = self.options
        
        def get_layers(element):
            return element.xpath("svg:g[@inkscape:groupmode='layer']")

        def is_layer(element):
            return element.get('inkscape:groupmode') == 'layer'

        if not get_layers(self.svg):
            inkex.errormsg("No layers found.")
            return False

        def can_write(path):
            while True:
                if os.path.exists(path) or not path:
                    break
                path = os.path.split(path)[0]
            return path and os.access(path, os.W_OK)

        def check_path():
            if not opts.path:
                inkex.errormsg("Please, choose an output filename/folder.")
                return False
            if opts.path.startswith('~') and os.getenv('HOME'):
                opts.path = opts.path.replace('~', os.getenv('HOME'), 1)
            opts.path = os.path.realpath(opts.path)
            if opts.codec == 'png':
                if os.path.exists(opts.path) and not os.path.isdir(opts.path):
                    inkex.errormsg(f'"{opts.path}" exists an it is not a folder.'
                                    ' Please, choose a folder for PNG sequence.')
                    return False
            else:
                if os.path.exists(opts.path) and os.path.isdir(opts.path):
                    inkex.errormsg(f'"{opts.path}" is an existing folder.'
                                    ' Please, choose a file name to save animation to.')
                    return False
            if not can_write(opts.path):
                inkex.errormsg(f'Could not write to "{opts.path}".'
                                ' Please choose another location.')
                return False
            
        if check_path() is False:
            return False

    # layer manipulation functions
        # hidden layer tags have priority over exposed
        hidden_layer_tags = 'hide', 'hidden', 'off', 'temp', 'guides'
        exposed_layer_tags = 'bg', 'background', 'fg', 'foreground'

        def layer_label_in(layer, tags):
            label = layer.get('inkscape:label')
            label = (label or layer.get('id') or '').lower()
            return label in tags or any(f'[{tag}]' in label for tag in tags)

        def show_element(element, show=True):
            if layer_label_in(element, exposed_layer_tags):
                element.style.update('display:inherit;')
            elif show and not layer_label_in(element, hidden_layer_tags):
                element.style.update('display:inherit;' + 'opacity:1;'*opts.opac)
            else:
                element.style.update('display:none;')

        def show_parent_layers(layer, show=True):
            parent = layer
            while True:
                parent = parent.getparent()
                if not is_layer(parent):
                    break
                show_element(parent, show=show)

    # render functions
        svg_path = os.path.split(opts.input_file)[0]
        formats_with_alpha = ['webm_420', 'prores', 'png', 'apng', 'gif']
        opts.tran = opts.tran and opts.codec in formats_with_alpha
        
        def execute(args, stdout=sys.stderr):
            if not stdout:
                stdout = subprocess.DEVNULL
            subprocess.run(args, stdout=stdout)
        
        # for hrefs to work a frame must be saved under the original path
        def write_temp_svg(document):
            'Returns a temporary filename to remove later'
            fd, name = tempfile.mkstemp(dir=svg_path, prefix='ink_ext_l2a_', 
                                        suffix='.svg')
            f = os.fdopen(fd, 'wb')
            document.write(f)
            f.close()
            return name

        def rsvg_snapshot(svg_name, png_name):
            width = round(self.svg.viewport_width * opts.scale / 100)
            bg = 'none' if opts.tran else self.svg.namedview.get('pagecolor')
            execute(['rsvg-convert', '-a', '-w', str(width), '-b', bg, 
                     '-o', png_name, svg_name])
            
        def inkscape_snapshot(svg_name, png_name):
            dpi = 96 * opts.scale / 100
            opacity = 0 if opts.tran else 255
            inkscape(svg_name, export_filename=png_name, 
                     export_dpi=dpi, export_background_opacity=opacity)

        if opts.rsvg:
            try:
                execute(['rsvg-convert', '-v'], None)
                snapshot = rsvg_snapshot
            except FileNotFoundError:
                inkex.errormsg("`rsvg-convert` not found,"
                               " Inkscape is used as renderer.")
                snapshot = inkscape_snapshot
        else:
            snapshot = inkscape_snapshot

        def export_png(i, total_count):
            svg_name = write_temp_svg(self.document)
            png_name = os.path.join(self.tempdir, f'{i:04}.png')
            snapshot(svg_name, png_name)
            if opts.backandforth and total_count > 2:
                if i in range(1, total_count-1):
                    i = total_count * 2 - 2 - i
                    png2_name = os.path.join(self.tempdir, f'{i:04}.png')
                    copyfile(png_name, png2_name)
            os.remove(svg_name)
        
    # filter frame layers or objects
        frame_layers = []

        def filter_objects(elements, show=False):
            'Frame is any frirst level object'
            for element in elements:
                if is_layer(element):
                    show_element(element, show=True)
                    if layer_label_in(element, hidden_layer_tags):
                        continue
                    show_next = layer_label_in(element, exposed_layer_tags)
                    filter_objects(element.getchildren(), show_next)
                else:
                    show_element(element, show)
                    if show == False:
                        special_tags = hidden_layer_tags + exposed_layer_tags
                        if not layer_label_in(element, special_tags):
                            frame_layers.append(element)
            
        def filter_layers(layers, show=False, append=True):
            'Frame is only a leaf layer'
            for layer in layers:
                show_element(layer, show)
                if layer_label_in(layer, hidden_layer_tags):
                    continue
                children_layers = get_layers(layer)
                if layer_label_in(layer, exposed_layer_tags):
                    if children_layers:
                        filter_layers(children_layers, append=False, show=True)
                elif children_layers:
                    filter_layers(children_layers, show, append)
                elif append:
                    frame_layers.append(layer)
        
        layers = get_layers(self.svg)
        
        if opts.firstlev:
            filter_objects(layers)
        else:
            filter_layers(layers)

        total_count = len(frame_layers)
        
        if total_count == 0:
            inkex.errormsg("Nothing to do.")
            return False
            
    # render frames
        for i,layer in enumerate(frame_layers):
            show_parent_layers(layer, show=True)
            show_element(layer, show=True)
            export_png(i, total_count)
            show_element(layer, show=False)
            show_parent_layers(layer, show=False)

        if opts.backandforth and total_count > 2:
            total_count = total_count * 2 - 2

    # encode
        def ffplay(what, *args):
            if opts.ffplay:
                try:
                    execute(['ffplay', '-loglevel', 'quiet', *args,
                             '-vf', f'loop=-1:{total_count}', what], None)
                except FileNotFoundError:
                    inkex.errormsg("`ffplay` not found,"
                                   " the animation will not be played.")

        def extend(path, ext):
            folder = os.path.split(path)[0]
            if not os.path.exists(folder):
                os.makedirs(folder)
            if path.lower().endswith(ext):
                ext = ''
            return path + ext
            
        input = os.path.join(self.tempdir, '%04d.png')
        ffargs = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'warning', 
                  '-framerate', str(opts.fps), '-i', input]
        
        # PNG
        if opts.codec == 'png':
            if not os.path.exists(opts.path):
                os.makedirs(opts.path)
            output = os.path.join(opts.path, '%04d.png')
            execute(ffargs + ['-c', 'copy', '-start_number', str(opts.pngn),
                              output])
            # `input` is played: for ffplay it's easier to play image 
            # file sequence starting from file 0 rather than `opts.pngn`
            ffplay(input, '-framerate', str(opts.fps))

        # APNG
        elif opts.codec == 'apng':
            output = extend(opts.path, '.png')
            execute(ffargs + ['-plays', '0', '-f', 'apng', output])
            ffplay(output)

        # GIF
        elif opts.codec == 'gif':
            # https://ffmpeg.org/ffmpeg-filters.html#palettegen
            output = extend(opts.path, '.gif')
            palette = os.path.join(self.tempdir, 'palette.png')
            loglevel = ['-loglevel', 'error']
            execute(ffargs + ['-vf', 'palettegen=256', palette, *loglevel])
            execute(ffargs + ['-i', palette, '-filter_complex', 
                              f'paletteuse=floyd_steinberg', output])
            ffplay(output)

        # other formats
        else:
            codec, pix_fmt, ext = {
                'mp4'      : ('libx264',    'yuv444p',      '.mp4' ),
                'mp4_rgb'  : ('libx264rgb', 'rgb24',        '.mp4' ),
                'mp4_420'  : ('libx264',    'yuv420p',      '.mp4' ),
                'webm'     : ('vp9',        'yuv444p',      '.webm'),
                'webm_rgb' : ('vp9',        'bgrp',         '.webm'),
                'webm_420' : ('vp9',        'yuva420p',     '.webm'),
                'prores'   : ('prores_ks',  'yuva444p10le', '.mov' )
            }[opts.codec]
            
            output = extend(opts.path, ext)
            vf = f'format={pix_fmt},loop={opts.loops-1}:{total_count}'
            
            if   opts.codec.startswith('mp4'):    
                crf = ['-crf', str(min(opts.crf, 51))]
            elif opts.codec.startswith('webm'):   
                crf = ['-crf', str(opts.crf), '-b:v', '0']
            elif opts.codec.startswith('prores'): 
                crf = ['-profile:v', '4444']  # not a crf
            
            execute(ffargs + ['-vf', vf, '-c:v', codec, *crf, output])
            ffplay(output)

    # document should stay unchanged
        # Inkscape has no facility to define an `OutputExtension` which outputs
        # in multiple formats. It is not bad in our case, because `EffectExtension`
        # (or it's analog, in our case) can be repeatedly invoked with "Alt+Q"
        # shotrcut without a need to redefine the parameters including a path
        # to a video file. Another issue is that Inkscape always expects an SVG
        # formatted string from an extension's `stdout` and will always `rebase()`
        # (overwrite) an open document with that string, so even if an extension
        # does not change a document it must write original one to its stdout,
        # otherwise Inkscape complains with the 'The output from the extension
        # could not be parsed' message.
        # 
        # `SvgInputMixin` stores originl SVG in `self.original_document`,
        # `SvgOutputMixin` defines proper `self.save()` method to pass an SVG
        # to Inkscape (over stdout) after an effect has been applied.
        # `SvgThroughMixin` (not used in this extension), combining both the above
        # mixins defines an unsuitable (in our case) method for testing whether
        # a document has changed. In our case a document may not change, that's
        # why two separate mixins are used.
        #
        self.document = self.original_document
        return
            
if __name__ == '__main__':
    Layers2Anim().run()
