from __future__ import print_function
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.properties import (
    NumericProperty, ListProperty, ObjectProperty, DictProperty)
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.app import App

from functools import partial
from copy import copy
from math import pi

KV = '''
#:import pi math.pi
#:import cos math.cos
#:import sin math.sin
#:import V kivy.vector.Vector
<ModernMenu>:
    canvas.before:
        Color:
            rgba: root.cancel_color
        Ellipse:
            pos: self.center_x - self.radius, self.center_y - self.radius
            size: self.radius * 2, self.radius * 2
            angle_start: 0
            angle_end: self.circle_progress * 360 * self.creation_direction
        Color:
            rgba: self.color
        Line:
            circle:
                (
                self.center_x, self.center_y,
                self.radius, 0,
                self.circle_progress * 360 * self.creation_direction
                )
            width: self.line_width
    on_touch_down:
        V(args[1].pos).distance(self.center) < self.radius and (
        self.back() if self.choices_history else self.dismiss())
<ModernMenuLabel>:
    size: self.texture_size
    padding: 5, 5
    halign: 'center'
    valign: 'middle'
    on_press: self.callback and self.callback(self)
    canvas.before:
        Color:
            rgba: self.bg_color
        Rectangle:
            pos: self.pos
            size: self.size
        Line:
            points:
                (
                self.center_x, self.center_y,
                self.parent.center_x + cos(
                self.start_angle +
                self.opacity * self.index_adj * self.angle / self.siblings_adj
                ) * self.parent.radius,
                self.parent.center_y + sin(
                self.start_angle +
                self.opacity * self.index_adj * self.angle / self.siblings_adj
                ) * self.parent.radius
                ) if self.parent else []
            width: self.parent.line_width if self.parent else 1
    center:
        (
        self.parent.center_x +
        cos(self.start_angle +
        self.opacity * self.index_adj * self.angle / self.siblings_adj
        ) * self.radius,
        self.parent.center_y +
        sin(self.start_angle +
        self.opacity * self.index_adj * self.angle / self.siblings_adj
        ) * self.radius
        ) if (self.size and self.parent and self.parent.children) else (0, 0)
'''


def squared_dist(p1, p2):
    (x1, y1) = p1
    (x2, y2) = p2
    return (x1 - x2) ** 2 + (y1 - y2) ** 2


class ModernMenuLabel(ButtonBehavior, Label):
    index = NumericProperty(0)
    radius = NumericProperty(200)
    siblings = NumericProperty(1)
    callback = ObjectProperty(None)
    bg_color = ListProperty([.1, .4, .4, .9])

    def calculate_angle(self, *args):
        if self.parent is None:
            return
        factor = 2.0
        self.start_angle = 0
        left = top = False
        if self.parent.center_x < self.radius:
            factor /= 2
            self.start_angle = 1.5 * pi
            left = True
        if self.parent.center_y < self.radius:
            factor /= 2
            self.start_angle = 0
        if self.parent.parent:
            if self.parent.center_y + self.radius > self.parent.parent.height:
                factor /= 2
                self.start_angle = 1.5 * pi if left else pi
                top = True
            if self.parent.center_x + self.radius > self.parent.parent.width:
                factor /= 2
                self.start_angle = pi if top else pi / 2
        self.angle = factor * pi
        # index adjustment: if 1, the items will spread the whole angle,
        #                   which is what we want if angle is < 2 * pi
        #                   if angle is 2 * pi, first item would be at the
        #                   same location as the last one, so we set 0
        idx_adj = 0 if factor == 2 else 1
        self.index_adj = self.index - idx_adj
        self.siblings_adj = max(1, self.siblings - idx_adj)

    def on_parent(self, *args):
        if self.parent:
            self.parent.bind(children=self.update_siblings,
                             center=self.calculate_angle)
            if self.parent.parent:
                self.parent.parent.bind(size=self.calculate_angle)
            self.calculate_angle()

    def update_siblings(self, *args):
        if self.parent:
            self.siblings = max(1, len(self.parent.children))
        else:
            self.siblings = 1
        self.calculate_angle()


class ModernMenu(Widget):
    radius = NumericProperty(50)
    circle_width = NumericProperty(5)
    line_width = NumericProperty(2)
    color = ListProperty([.3, .3, .3, 1])
    circle_progress = NumericProperty(0)
    creation_direction = NumericProperty(1)
    creation_timeout = NumericProperty(1)
    choices = ListProperty([])
    item_cls = ObjectProperty(ModernMenuLabel)
    item_args = DictProperty({'opacity': 0})
    animation = ObjectProperty(Animation(opacity=1, d=.5))
    choices_history = ListProperty([])
    cancel_color = ListProperty([1, 0, 0, .4])

    def start_display(self, touch):
        touch.grab(self)
        a = Animation(circle_progress=1, d=self.creation_timeout)
        a.bind(on_complete=self.open_menu)
        touch.ud['animation'] = a
        a.start(self)

    def open_menu(self, *args):
        self.clear_widgets()
        for i in self.choices:
            kwargs = copy(self.item_args)
            kwargs.update(i)
            ml = self.item_cls(**kwargs)
            self.animation.start(ml)
            self.add_widget(ml)

    def open_submenu(self, choices, *args):
        self.choices_history.append(self.choices)
        self.choices = choices
        self.open_menu()

    def back(self, *args):
        self.choices = self.choices_history.pop()
        self.open_menu()

    def on_touch_move(self, touch, *args):
        if (
            touch.grab_current == self and
            squared_dist(touch.pos, touch.opos) > self.radius ** 2 and
            self.parent and
            self.circle_progress < 1
        ):
            self.parent.remove_widget(self)

        return super(ModernMenu, self).on_touch_move(touch, *args)

    def on_touch_up(self, touch, *args):
        if (
            touch.grab_current == self and
            self.parent and
            self.circle_progress < 1
        ):
            self.parent.remove_widget(self)
        return super(ModernMenu, self).on_touch_up(touch, *args)

    def dismiss(self):
        a = Animation(opacity=0)
        a.bind(on_complete=self._remove)
        a.start(self)

    def _remove(self, *args):
        if self.parent:
            self.parent.remove_widget(self)


class MenuSpawner(Widget):
    timeout = NumericProperty(0.1)
    menu_cls = ObjectProperty(ModernMenu)
    cancel_distance = NumericProperty(10)
    menu_args = DictProperty({})

    def on_touch_down(self, touch, *args):
        t = partial(self.display_menu, touch)
        touch.ud['menu_timeout'] = t
        Clock.schedule_once(t, self.timeout)
        return super(MenuSpawner, self).on_touch_down(touch, *args)

    def on_touch_move(self, touch, *args):
        if (
            touch.ud['menu_timeout'] and
            squared_dist(touch.pos, touch.opos) > self.cancel_distance ** 2
        ):
            Clock.unschedule(touch.ud['menu_timeout'])
        return super(MenuSpawner, self).on_touch_move(touch, *args)

    def on_touch_up(self, touch, *args):
        if touch.ud.get('menu_timeout'):
            Clock.unschedule(touch.ud['menu_timeout'])
        return super(MenuSpawner, self).on_touch_up(touch, *args)

    def display_menu(self, touch, dt):
        menu = self.menu_cls(center=touch.pos, **self.menu_args)
        self.add_widget(menu)
        menu.start_display(touch)


Builder.load_string(KV)

TESTAPP_KV = '''
FloatLayout:
    ScrollView:
        BoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: 1000
            Label:
                text: 'Mexican'
                bcolor: 1,0,0,1
            Button:
                text: 'Italian'
            Label:
                text: 'American'
            Button:
                text: 'Polish'
    MenuSpawner:
        timeout: .8
        menu_args:
            dict(
            creation_direction=-1,
            radius=45,
            creation_timeout=.4,
            choices=[
            
            dict(text='Drinks', index=1, callback=app.callback1),
            dict(text='Appetizers', index=2, callback=app.callback3),
            dict(text='Lunch Specials', index=3, callback=app.callback4),
            dict(text='Dinner', index=4, callback=app.callback5),
            dict(text='Desert', index=5, callback=app.callback6),
            
            
            
            # dict(text='action 1', index=2, callback=app.callback2),
            # dict(text='action 2', index=3, callback=app.callback3),
            
            ])
'''


class CustomPopUp(Popup):
    pass


def open_popup(self):
    self.box = BoxLayout(orientation='vertical', spacing=10)

    self.box.add_widget(Label(text='This is what you ordered'))

    self.buttonsplace = BoxLayout(orientation='horizontal', size_hint=(.999, 0))

    self.the_popup = CustomPopUp(
        title='YOUR ORDER',
        content=self.box,
        size_hint=(None, None), size=(1200, 900)
    )

    self.buttonsplace.add_widget(Button(
        text='Cancel',
        on_press=lambda *args: self.the_popup.dismiss()
    ))
    self.buttonsplace.add_widget(Button(text='Complete Order'))
    self.box.add_widget(self.buttonsplace)

    self.the_popup.open()


class ModernMenuApp(App):
    def build(self):
        return Builder.load_string(TESTAPP_KV)

    def callback1(self, *args):
        print("Drink added")
        args[0].parent.open_submenu(
            choices=[
                dict(text='Coke ... $1.50', index=1, callback=self.callback2),
                dict(text='Beer ... $5.50', index=2, callback=self.callback2),
                dict(text='Tea ... $1.00', index=3, callback=self.callback2),
                dict(text='Coffee ... $3.50', index=4, callback=self.callback2),
                dict(text='Wine ... $5.50', index=5, callback=self.callback2),
            ])

    def callback2(self, *args):
        print("Action completed")
        open_popup(self)
        args[0].parent.dismiss()

    def callback3(self, *args):
        print("Appetizer added")
        args[0].parent.open_submenu(
            choices=[
                dict(text='Mini Tacos ... $4.50', index=1, callback=self.callback2),
                dict(text='Bites ... $2.50', index=2, callback=self.callback2),
                dict(text='Pop Corn ... $3.00', index=3, callback=self.callback2),
                dict(text='Mini Burgers ... $5.50', index=4, callback=self.callback2),
                dict(text='Wonton ... $8.50', index=5, callback=self.callback2),
            ])

    def callback4(self, *args):
        print("Lunch special added")
        args[0].parent.open_submenu(
            choices=[
                dict(text='Special Wings ... $7.50', index=1, callback=self.callback2),
                dict(text='Special Nachos ... $8.50', index=2, callback=self.callback2),
                dict(text='Special Hummus ... $2.00', index=3, callback=self.callback2),
                dict(text='Special Empanadas ... $7.50', index=4, callback=self.callback2),
                dict(text='Special Rib ... $10.50', index=5, callback=self.callback2),
            ])

    def callback5(self, *args):
        print("Dinner added")
        args[0].parent.open_submenu(
            choices=[
                dict(text='Chicken Wings ... $15.50', index=1, callback=self.callback2),
                dict(text='Ultimate Nachos ... $12.50', index=2, callback=self.callback2),
                dict(text='Hummus ... $3.00', index=3, callback=self.callback2),
                dict(text='Beef Empanadas ... $15.50', index=4, callback=self.callback2),
                dict(text='Prime Rib ... $18.50', index=5, callback=self.callback2),
            ])

    def callback6(self, *args):
        print("Dessert added")
        args[0].parent.open_submenu(
            choices=[
                dict(text='Apple Pie ... $5.50', index=1, callback=self.callback2),
                dict(text='Ice Cream ... $6.50', index=2, callback=self.callback2),
                dict(text='Carrot Cake ... $4.00', index=3, callback=self.callback2),
                dict(text='Cheesecake ... $7.50', index=4, callback=self.callback2),
                dict(text='Tiramisu ... $7.50', index=5, callback=self.callback2),
            ])


modern_menu_app = ModernMenuApp()
modern_menu_app.run()

