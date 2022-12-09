import inkex
from inkex.base import TempDirMixin
from inkex.command import take_snapshot as inkscape_snapshot, write_svg
import os, subprocess as sp, shutil, sys

class AnimLayers(TempDirMixin, inkex.OutputExtension):
    def add_arguments(self, pars):
        pars.add_argument('--resolution', type=int, default=96)
        pars.add_argument('--fps', type=int, default=12)
        pars.add_argument('--loops', type=int, default=1)
        pars.add_argument('--crf',  type=int, default=22)
        pars.add_argument('--opac', type=inkex.Boolean, default=True)
        pars.add_argument('--firstlev', type=inkex.Boolean, default=False)
        pars.add_argument('--rgb',  type=inkex.Boolean, default=True)
        pars.add_argument('--rsvg', type=inkex.Boolean, default=True)
        pars.add_argument('--pngs', type=inkex.Boolean, default=False)
        pars.add_argument('--path', type=str, default='')
        pars.add_argument('--pngn', type=int, default=0)
        pars.add_argument('--ffplay', type=inkex.Boolean, default=False)

    def save(self, stream):
        layers = self.svg.xpath("//svg:g[@inkscape:groupmode='layer']")

        if len(layers) < 1:
            inkex.errormsg("No layers found.")
            return

        if self.options.pngs:
            if not self.options.path:
                inkex.errormsg("PNG frames will not be saved. Please, choose a path.")
                # TODO: export MP4 anyway
                return
            if not os.path.exists(self.options.path):
                os.mkdir(self.options.path)
            elif not os.path.isdir(self.options.path):
                inkex.errormsg(f'"{self.options.path}" is not a directory.')
                return

        exposed_layer_names = 'bg', 'background', 'fg', 'foreground', 'show', 'nohide'
        hidden_layer_names = 'hide', 'hidden', 'scratch', 'temp', 'guides'

        def label(layer):
            layer_label = layer.get('inkscape:label')
            return layer_label and layer_label.lower() or ''

        def show_layer(layer, show=True):
            if show or label(layer) in exposed_layer_names:
                layer.style.update('display:inherit;' + 'opacity:1;' * self.options.opac)
            else:
                layer.style.update('display:none;')

        def is_layer(obj):
            return obj.get('inkscape:groupmode') == 'layer'

        def show_parent_layers(layer, show=True):
            parent = layer
            while True:
                parent = parent.getparent()
                if is_layer(parent):
                    show_layer(parent, show=show)
                else:
                    break

        def rsvg_snapshot(document, dirname, name, dpi, **kwargs):
            path = os.path.join(dirname, name)
            width = round(self.svg.viewport_width * dpi / 96)
            bg = self.svg.namedview.get('pagecolor')
            write_svg(document, path+'.svg')
            args = f'rsvg-convert -w {width} -a -b {bg} -o {path}.png {path}.svg'
            sp.run(args.split())

        if self.options.rsvg:
            snapshot = rsvg_snapshot
        else:
            snapshot = inkscape_snapshot

        # filter frame and bg layers
        frame_layers = []

        def filter_layers(layers, firstlev=False):
            for layer in layers:
                # hide everything except bg
                show_layer(layer, show=False)
                # select regular leaf layers or their first level objects
                if label(layer) not in [*hidden_layer_names, *exposed_layer_names]:
                    children = layer.getchildren()
                    has_children_layers = any(is_layer(c) for c in children)
                    if has_children_layers:
                        continue
                    elif firstlev:
                        filter_layers(children)
                    else:
                        frame_layers.append(layer)

        filter_layers(layers, self.options.firstlev)

        for i,layer in enumerate(frame_layers):
            show_parent_layers(layer)
            show_layer(layer)
            snapshot(self.document, dirname=self.tempdir, name=f'{i:04}',
                     dpi=self.options.resolution, export_background_opacity=255)
            show_layer(layer, show=False)
            show_parent_layers(layer, show=False)

            # copy PNG file if the option enabled
            if self.options.pngs:
                f = os.path.join(self.tempdir, f'{i:04}.png')
                t = os.path.join(self.options.path, f'{i+self.options.pngn:04}.png')
                shutil.copyfile(f, t)

        # convert to mp4
        fps   = self.options.fps
        crf   = self.options.crf
        codec = ['libx264', 'libx264rgb'][self.options.rgb]
        pngs  = os.path.join(self.tempdir, '%04d.png')
        mp4   = os.path.join(self.tempdir, 'temp.mp4')
        loglevel  = '-hide_banner -loglevel warning'
        vf_loops  = f'loop={self.options.loops-1}:{i}'
        args = f'''
            ffmpeg
                {loglevel}
                -framerate {fps} -i {pngs}
                -vf {vf_loops}
                -c:v {codec} -crf {crf}
               {mp4}
        '''
        sp.run(args.split())

        # save output
        with open(mp4, 'rb') as tmp4:
            shutil.copyfileobj(tmp4, stream)

        if self.options.ffplay:
            sp.run(f'ffplay -loglevel quiet -loop 0 {mp4}'.split())

if __name__ == '__main__':
    AnimLayers().run()
