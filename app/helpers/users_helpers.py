from PIL import ImageDraw, Image
import numpy as np
import hashlib
import io
from flask_login import current_user
from .general_helpers import SidebarElement, SidebarElementSublink, CurrentObjectAction, CurrentObjectInfo
from .main_page_helpers import DefaultSidebar as MainPageSidebar
import datetime
from flask import url_for, current_app, redirect, request, flash
from flask_babel import lazy_gettext as _l, LazyString
import functools
from typing import Callable, List
import app.models as models


def generate_avatar(avatar_size: int, nickname: str, extension="png") -> None:
    ''' A function that generates an avatar with a size of 12x12 blocks based on a nickname.
        Taken from the Internet, slightly upgraded.
        Parameters: (avatar_size, nickname, extension),
        where avatar_size is the size of the avatar in pixels, nickname is the nickname for which the image is generated, extension is the extension of the specified image'''
    if avatar_size % 12 != 0:
        raise ValueError("The size of the image must be a multiple of 12!")
    background_color = '#f2f1f2'
    s = nickname
    # We get a set of pseudo-random bytes
    digital_string = hashlib.md5(s.encode('utf-8')).digest()
    # Получаем цвет из хеша
    main_color = digital_string[:3]
    main_color = tuple(channel // 2 + 128 for channel in main_color)
    # Generating a block filling matrix
    # an array of 6 by 12
    need_color = np.array([bit == '1' for byte in digital_string[3:3+9] for bit in bin(byte)[2:].zfill(8)]).reshape(6, 12)
    # we get a 12 by 12 matrix by reflecting a 6x12 matrix
    need_color = np.concatenate((need_color, need_color[::-1]), axis=0)
    for i in range(12):
        need_color[0, i] = 0
        need_color[11, i] = 0
        need_color[i, 0] = 0
        need_color[i, 11] = 0
    # We draw images according to the filling matrix
    img_size = (avatar_size, avatar_size)
    block_size = avatar_size // 12  # the size of the square
    img = Image.new('RGB', img_size, background_color)
    draw = ImageDraw.Draw(img)
    for x in range(avatar_size):
        for y in range(avatar_size):
            need_to_paint = need_color[x // block_size, y // block_size]
            if need_to_paint:
                draw.point((x, y), main_color)
    img_bytes = io.BytesIO()
    img.save(img_bytes, extension)
    return img_bytes.getvalue()


class UserSidebar:
    def __init__(self, user, current_object):
        se11 = SidebarElementSublink(_l("Main information"), url_for('users.user_show', user_id=user.id), current_object=='user_show')
        se12 = SidebarElementSublink(_l("Edit"), url_for('users.user_edit', user_id=user.id), current_object=='user_edit')
        sel3 = SidebarElementSublink(_l("Change password"), url_for('users.user_change_password_callback', user_id=user.id), current_object=='user_password_change')
        se1 = SidebarElement(_l("Profile"), url_for('users.user_show', user_id=user.id), 'fa-solid fa-user-tie', current_object in ['user_show', 'user_edit', 'user_password_change'], [se11, se12, sel3])
        
        self.se = [se1]

    def __call__(self) -> List[SidebarElement]:
        return self.se
