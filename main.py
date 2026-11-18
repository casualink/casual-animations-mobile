
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.togglebutton import ToggleButton
from kivy.graphics import Color, Line, Rectangle, Ellipse
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.uix.colorpicker import ColorPicker
import copy

# CORES
DARK = "#1A1A22"
DARK2 = "#24242F"
ACCENT = "#7C5CFF"
GREEN = "#22C55E"
ORANGE = "#F59E0B"
RED = "#EF4444"

W, H = 700, 400

class CanvasDesenho(Widget):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref
        self.size_hint = (None, None)
        self.size = (W, H)
        # dados: frames = lista de {camada1: lista de traços, camada2: lista}
        # cada traço = dict {tool, color, width, points, rect}
        self.bind(pos=self.redesenha, size=self.redesenha)

    def redesenha(self, *a):
        self.canvas.clear()
        with self.canvas:
            Color(1,1,1,1)
            Rectangle(pos=self.pos, size=self.size)
            # Onion Skin
            app = self.app_ref
            if app.onion_on and app.current_frame > 0 and not app.is_playing:
                prev = app.frames[app.current_frame-1]
                for camada in ["Camada 1", "Camada 2"]:
                    for t in prev[camada]:
                        r,g,b,a = t['color']
                        Color(r,g,b,0.22)
                        if t['tool'] in ['pen','eraser','line']:
                            Line(points=self.converte(t['points']), width=t['width'], cap='round', joint='round')
                        elif t['tool']=='rect':
                            Line(rectangle=self.converte_rect(t['rect']), width=t['width'])
                        elif t['tool']=='circle':
                            Line(ellipse=self.converte_rect(t['rect']), width=t['width'])
            # Frame atual
            cur = app.frames[app.current_frame]
            for camada in ["Camada 1", "Camada 2"]:
                for t in cur[camada]:
                    if t['tool']=='eraser':
                        # borracha apaga desenhando branco
                        Color(1,1,1,1)
                    else:
                        Color(*t['color'])
                    if t['tool'] in ['pen','eraser','line']:
                        Line(points=self.converte(t['points']), width=t['width'], cap='round', joint='round')
                    elif t['tool']=='rect':
                        Line(rectangle=self.converte_rect(t['rect']), width=t['width'])
                    elif t['tool']=='circle':
                        Line(ellipse=self.converte_rect(t['rect']), width=t['width'])
            # Preview da forma atual
            if app.preview_shape:
                Color(*app.brush_color)
                if app.active_tool=='line':
                    Line(points=self.converte(app.preview_shape), width=app.brush_size)
                elif app.active_tool=='rect':
                    Line(rectangle=self.converte_rect(app.preview_shape), width=app.brush_size)
                elif app.active_tool=='circle':
                    Line(ellipse=self.converte_rect(app.preview_shape), width=app.brush_size)

    def converte(self, pts):
        # pts em 0..W, 0..H -> pos real
        out=[]
        for i in range(0,len(pts),2):
            out.append(self.x + pts[i])
            out.append(self.y + pts[i+1])
        return out

    def converte_rect(self, r):
        x1,y1,x2,y2 = r
        return (self.x+min(x1,x2), self.y+min(y1,y2), abs(x2-x1), abs(y2-y1))

    def to_local(self, touch):
        return (touch.x - self.x, touch.y - self.y)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        app = self.app_ref
        if app.is_playing:
            app.toggle_play()
        if app.active_tool == 'picker':
            # pega cor do último traço próximo (simplificado)
            app.set_color("#FF0000")
            return True
        if app.active_tool == 'bucket':
            app.save_history()
            # balde = pinta fundo da camada com cor (efeito simples)
            cur = app.frames[app.current_frame][app.active_layer]
            cur.append({'tool':'rect','color':app.brush_color,'width':1,'rect':[0,0,W,H],'points':[]})
            self.redesenha()
            return True
        app.save_history()
        lx, ly = self.to_local(touch)
        app.start_pos = (lx, ly)
        app.current_points = [lx, ly]
        if app.active_tool in ['line','rect','circle']:
            app.preview_shape = [lx, ly, lx, ly] if app.active_tool=='line' else [lx, ly, lx, ly]
        else:
            app.current_points = [lx, ly]
        return True

    def on_touch_move(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        app = self.app_ref
        if app.active_tool in ['bucket','picker']:
            return True
        lx, ly = self.to_local(touch)
        if app.active_tool in ['line','rect','circle']:
            sx, sy = app.start_pos
            app.preview_shape = [sx, sy, lx, ly]
            self.redesenha()
        else:
            app.current_points += [lx, ly]
            # desenha temporário
            self.redesenha()
            # desenha linha atual por cima
            with self.canvas:
                if app.active_tool=='eraser':
                    Color(1,1,1,1)
                    w = app.brush_size+8
                else:
                    Color(*app.brush_color)
                    w = app.brush_size
                Line(points=self.converte(app.current_points), width=w, cap='round', joint='round')
        return True

    def on_touch_up(self, touch):
        app = self.app_ref
        if app.active_tool in ['bucket','picker'] or app.start_pos is None:
            app.start_pos=None
            app.preview_shape=None
            return True
        lx, ly = self.to_local(touch)
        cur = app.frames[app.current_frame][app.active_layer]
        if app.active_tool in ['line','rect','circle']:
            sx, sy = app.start_pos
            if app.active_tool=='line':
                cur.append({'tool':'line','color':app.brush_color,'width':app.brush_size,'points':[sx,sy,lx,ly],'rect':[]})
            else:
                cur.append({'tool':app.active_tool,'color':app.brush_color,'width':app.brush_size,'points':[],'rect':[sx,sy,lx,ly]})
        else:
            cur.append({'tool':app.active_tool,'color':app.brush_color,'width':app.brush_size+8 if app.active_tool=='eraser' else app.brush_size,'points':list(app.current_points),'rect':[]})
        app.preview_shape=None
        app.start_pos=None
        self.redesenha()
        return True

class FlipaClipKivyApp(App):
    def build(self):
        self.title = "FlipaClip Kivy Pro"
        self.frames = [{"Camada 1": [], "Camada 2": []}]
        self.current_frame = 0
        self.active_layer = "Camada 2"
        self.active_tool = "pen"
        self.brush_color = (0,0,0,1)
        self.base_color_hex = "#000000"
        self.brush_size = 6
        self.fps = 12
        self.is_playing = False
        self.onion_on = True
        self.history = {0: {"undo": [], "redo": []}}
        self.start_pos = None
        self.current_points = []
        self.preview_shape = None
        self.play_event = None

        root = BoxLayout(orientation='vertical', spacing=0)

        # TOPO
        topo = BoxLayout(size_hint_y=None, height=dp(56), padding=dp(8), spacing=dp(8))
        self.bg(topo, DARK)
        topo.add_widget(Label(text="🎬 FLIPACLIP KIVY", font_size=dp(16), bold=True, color=(1,1,1,1), size_hint_x=1.2))
        topo.add_widget(Label(text="Espessura:", color=(1,1,1,1), size_hint_x=None, width=dp(75)))
        self.slider_brush = Slider(min=1, max=30, value=self.brush_size, size_hint_x=1)
        self.slider_brush.bind(value=lambda s,v: setattr(self,'brush_size',int(v)))
        topo.add_widget(self.slider_brush)
        topo.add_widget(Label(text="FPS:", color=(1,1,1,1), size_hint_x=None, width=dp(35)))
        self.slider_fps = Slider(min=1, max=24, value=self.fps, size_hint_x=0.8)
        self.slider_fps.bind(value=lambda s,v: setattr(self,'fps',int(v)))
        topo.add_widget(self.slider_fps)
        btn_onion = ToggleButton(text="🧅 Onion", state='down', size_hint_x=None, width=dp(90), background_color=get_color_from_hex(ACCENT))
        btn_onion.bind(on_press=lambda x: setattr(self,'onion_on', x.state=='down') or self.canvas_widget.redesenha())
        topo.add_widget(btn_onion)
        root.add_widget(topo)

        # MEIO
        meio = BoxLayout(orientation='horizontal', padding=dp(8), spacing=dp(8))
        self.bg(meio, DARK)

        # ESQUERDA - FERRAMENTAS
        esquerda = BoxLayout(orientation='vertical', size_hint_x=None, width=dp(78), spacing=dp(6))
        self.bg(esquerda, DARK2)
        self.tool_btns = {}
        for nome, emoji in [("pen","✏️"),("eraser","🧽"),("bucket","🪣"),("line","📏"),("rect","⬛"),("circle","🔴")]:
            b = Button(text=f"{emoji}\n{nome}", font_size=dp(11), background_color=get_color_from_hex("#3A3A4D"), background_normal='', size_hint_y=None, height=dp(52))
            b.bind(on_press=lambda x, t=nome: self.set_tool(t))
            esquerda.add_widget(b)
            self.tool_btns[nome]=b
        esquerda.add_widget(Label(text="CORES", font_size=dp(10), color=(0.7,0.7,0.7,1), size_hint_y=None, height=dp(18)))
        cores = ["#000000","#FFFFFF","#FF0000","#FF9500","#FFCC00","#00FF00","#007AFF","#AF52DE","#FF5EA8","#8B4513"]
        grid = GridLayout(cols=2, size_hint_y=None, height=dp(100), spacing=dp(4))
        for c in cores:
            b = Button(background_color=get_color_from_hex(c), background_normal='', size_hint=(None,None), size=(dp(30),dp(18)))
            b.bind(on_press=lambda x, col=c: self.set_color(col))
            grid.add_widget(b)
        esquerda.add_widget(grid)
        btn_cor = Button(text="🌈 Cor", size_hint_y=None, height=dp(36), background_color=get_color_from_hex("#3B82F6"), background_normal='')
        btn_cor.bind(on_press=self.open_color_picker)
        esquerda.add_widget(btn_cor)
        meio.add_widget(esquerda)

        # CENTRO - CANVAS
        centro = FloatLayout()
        self.canvas_widget = CanvasDesenho(self)
        # centraliza
        centro.add_widget(self.canvas_widget)
        self.canvas_widget.pos_hint = {'center_x':0.5, 'center_y':0.5}
        meio.add_widget(centro)

        # DIREITA - CAMADAS + EFEITOS
        direita = BoxLayout(orientation='vertical', size_hint_x=None, width=dp(150), spacing=dp(6), padding=dp(8))
        self.bg(direita, DARK2)
        direita.add_widget(Label(text="CAMADAS", bold=True, color=(0.8,0.8,0.8,1), size_hint_y=None, height=dp(22)))
        self.btn_l2 = Button(text="🔲 Camada 2", background_color=get_color_from_hex("#2563EB"), background_normal='', size_hint_y=None, height=dp(38))
        self.btn_l2.bind(on_press=lambda x: self.set_layer("Camada 2"))
        direita.add_widget(self.btn_l2)
        self.btn_l1 = Button(text="🔳 Camada 1", background_color=get_color_from_hex("#3A3A4D"), background_normal='', size_hint_y=None, height=dp(38))
        self.btn_l1.bind(on_press=lambda x: self.set_layer("Camada 1"))
        direita.add_widget(self.btn_l1)
        direita.add_widget(Label(text="EFEITOS", bold=True, color=(0.8,0.8,0.8,1), size_hint_y=None, height=dp(22)))
        direita.add_widget(Label(text="Brilho do pincel", font_size=dp(11), color=(1,1,1,1), size_hint_y=None, height=dp(18)))
        s_brilho = Slider(min=0.3, max=2.0, value=1.0)
        s_brilho.bind(value=self.ajusta_brilho)
        direita.add_widget(s_brilho)
        direita.add_widget(Label(text="AÇÕES", bold=True, color=(0.6,0.6,0.6,1), size_hint_y=None, height=dp(22)))
        for txt, fn in [("↩ Desfazer", self.undo), ("↪ Refazer", self.redo), ("🗑️ Limpar", self.clear_frame)]:
            b = Button(text=txt, background_color=get_color_from_hex("#334155"), background_normal='', size_hint_y=None, height=dp(36))
            b.bind(on_press=lambda x, f=fn: f())
            direita.add_widget(b)
        direita.add_widget(Label(text="", size_hint_y=1))
        meio.add_widget(direita)
        root.add_widget(meio)

        # BAIXO - TIMELINE
        baixo = BoxLayout(size_hint_y=None, height=dp(68), padding=dp(8), spacing=dp(8))
        self.bg(baixo, DARK2)
        self.btn_play = Button(text="▶ Play", size_hint_x=None, width=dp(100), background_color=get_color_from_hex(GREEN), background_normal='', bold=True)
        self.btn_play.bind(on_press=lambda x: self.toggle_play())
        baixo.add_widget(self.btn_play)
        btn_prev = Button(text="◀", size_hint_x=None, width=dp(50), background_color=get_color_from_hex("#334155"), background_normal='')
        btn_prev.bind(on_press=lambda x: self.prev_frame())
        baixo.add_widget(btn_prev)
        self.lbl_frame = Label(text="Quadro 1 / 1", bold=True, color=(1,1,1,1))
        baixo.add_widget(self.lbl_frame)
        btn_next = Button(text="Próximo ➕", size_hint_x=None, width=dp(130), background_color=get_color_from_hex(ORANGE), background_normal='', color=(0,0,0,1), bold=True)
        btn_next.bind(on_press=lambda x: self.next_frame())
        baixo.add_widget(btn_next)
        btn_save = Button(text="💾 PNG", size_hint_x=None, width=dp(80), background_color=get_color_from_hex(RED), background_normal='', bold=True)
        btn_save.bind(on_press=lambda x: self.export_png())
        baixo.add_widget(btn_save)
        root.add_widget(baixo)

        self.set_tool("pen")
        Clock.schedule_once(lambda dt: self.canvas_widget.redesenha(), 0.1)
        return root

    def bg(self, widget, hexcolor):
        with widget.canvas.before:
            Color(*get_color_from_hex(hexcolor))
            Rectangle(pos=widget.pos, size=widget.size)
        def upd(*a):
            widget.canvas.before.clear()
            with widget.canvas.before:
                Color(*get_color_from_hex(hexcolor))
                Rectangle(pos=widget.pos, size=widget.size)
        widget.bind(pos=upd, size=upd)

    def set_tool(self, tool):
        self.active_tool = tool
        for k,b in self.tool_btns.items():
            b.background_color = get_color_from_hex(ACCENT) if k==tool else get_color_from_hex("#3A3A4D")
    def set_color(self, hexcol):
        self.base_color_hex = hexcol
        self.brush_color = get_color_from_hex(hexcol)
        self.brush_color = (self.brush_color[0], self.brush_color[1], self.brush_color[2], 1)
    def ajusta_brilho(self, s, v):
        # clareia a cor atual
        r,g,b,a = get_color_from_hex(self.base_color_hex)
        f = float(v)
        self.brush_color = (min(1,r*f), min(1,g*f), min(1,b*f), 1)
    def set_layer(self, layer):
        self.active_layer = layer
        self.btn_l1.background_color = get_color_from_hex("#2563EB") if layer=="Camada 1" else get_color_from_hex("#3A3A4D")
        self.btn_l2.background_color = get_color_from_hex("#2563EB") if layer=="Camada 2" else get_color_from_hex("#3A3A4D")
    def open_color_picker(self, *a):
        picker = ColorPicker()
        popup = Popup(title="Escolha a cor", content=picker, size_hint=(0.9,0.9))
        def escolheu(*x):
            c = picker.color
            hexcol = '#%02x%02x%02x' % (int(c[0]*255), int(c[1]*255), int(c[2]*255))
            self.set_color(hexcol)
            popup.dismiss()
        picker.bind(color=lambda *x: escolheu())
        popup.open()

    # Histórico
    def save_history(self):
        if self.current_frame not in self.history:
            self.history[self.current_frame]={"undo":[],"redo":[]}
        self.history[self.current_frame]["undo"].append(copy.deepcopy(self.frames[self.current_frame]))
        self.history[self.current_frame]["redo"].clear()
    def undo(self, *a):
        h = self.history.get(self.current_frame)
        if h and h["undo"]:
            h["redo"].append(copy.deepcopy(self.frames[self.current_frame]))
            self.frames[self.current_frame]=h["undo"].pop()
            self.canvas_widget.redesenha()
    def redo(self, *a):
        h = self.history.get(self.current_frame)
        if h and h["redo"]:
            h["undo"].append(copy.deepcopy(self.frames[self.current_frame]))
            self.frames[self.current_frame]=h["redo"].pop()
            self.canvas_widget.redesenha()
    def clear_frame(self, *a):
        self.save_history()
        self.frames[self.current_frame]={"Camada 1":[],"Camada 2":[]}
        self.canvas_widget.redesenha()

    # Timeline
    def next_frame(self):
        if self.is_playing: self.toggle_play()
        self.current_frame+=1
        if self.current_frame>=len(self.frames):
            self.frames.append({"Camada 1":[],"Camada 2":[]})
        if self.current_frame not in self.history:
            self.history[self.current_frame]={"undo":[],"redo":[]}
        self.atualiza_label()
        self.canvas_widget.redesenha()
    def prev_frame(self):
        if self.is_playing: self.toggle_play()
        if self.current_frame>0:
            self.current_frame-=1
            self.atualiza_label()
            self.canvas_widget.redesenha()
    def atualiza_label(self):
        self.lbl_frame.text=f"Quadro {self.current_frame+1} / {len(self.frames)}"
        if self.is_playing:
            self.lbl_frame.text=f"Play: {self.current_frame+1} / {len(self.frames)}"

    def toggle_play(self):
        if self.is_playing:
            self.is_playing=False
            if self.play_event: self.play_event.cancel()
            self.btn_play.text="▶ Play"
            self.btn_play.background_color=get_color_from_hex(GREEN)
            self.canvas_widget.redesenha()
            self.atualiza_label()
        else:
            self.is_playing=True
            self.btn_play.text="⏸ Parar"
            self.btn_play.background_color=get_color_from_hex(RED)
            self.play_idx=0
            self.play_event=Clock.schedule_interval(self.play_loop, 1.0/self.fps)
    def play_loop(self, dt):
        self.current_frame=self.play_idx
        self.canvas_widget.redesenha()
        self.atualiza_label()
        self.play_idx=(self.play_idx+1)%len(self.frames)

    def export_png(self):
        try:
            self.canvas_widget.export_to_png("meu_desenho.png")
            self.lbl_frame.text="✅ Salvo: meu_desenho.png"
        except Exception as e:
            self.lbl_frame.text=f"Erro: {e}"

if __name__=="__main__":
    FlipaClipKivyApp().run()