"""
UI utility functions for TB Scout.

This module provides utility functions for UI operations,
including creating actions, widgets, and other UI elements.
"""

from PyQt6.QtWidgets import QAction
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize

def create_action(parent, text, slot=None, shortcut=None, icon=None, 
                 tip=None, checkable=False, checked=False):
    """
    Create a QAction with the given properties.
    
    Args:
        parent: Parent widget for the action
        text: Text to display for the action
        slot: Function to call when action is triggered
        shortcut: Keyboard shortcut for the action
        icon: Icon to display for the action
        tip: Tooltip text
        checkable: Whether the action can be checked/unchecked
        checked: Initial checked state if checkable is True
        
    Returns:
        QAction instance
    """
    action = QAction(text, parent)
    if icon is not None:
        action.setIcon(icon)
    if shortcut is not None:
        action.setShortcut(shortcut)
    if tip is not None:
        action.setToolTip(tip)
        action.setStatusTip(tip)
    if slot is not None:
        action.triggered.connect(slot)
    if checkable:
        action.setCheckable(True)
        action.setChecked(checked)
    return action

def create_tool_button(parent, text, icon=None, tip=None, 
                      size=(32, 32), checkable=False):
    """
    Create a QToolButton with the given properties.
    
    Args:
        parent: Parent widget for the button
        text: Text to display for the button
        icon: Icon to display for the button
        tip: Tooltip text
        size: Size of the button as (width, height)
        checkable: Whether the button can be checked/unchecked
        
    Returns:
        QToolButton instance
    """
    from PyQt6.QtWidgets import QToolButton
    
    button = QToolButton(parent)
    button.setText(text)
    if icon is not None:
        button.setIcon(QIcon(icon))
    if tip is not None:
        button.setToolTip(tip)
    button.setIconSize(QSize(*size))
    if checkable:
        button.setCheckable(True)
    return button

def set_widget_margins(widget, left=0, top=0, right=0, bottom=0):
    """
    Set the margins of a widget.
    
    Args:
        widget: Widget to set margins for
        left: Left margin
        top: Top margin
        right: Right margin
        bottom: Bottom margin
    """
    widget.setContentsMargins(left, top, right, bottom)

def create_spacer(horizontal=True, fixed_size=None):
    """
    Create a spacer item for layouts.
    
    Args:
        horizontal: Whether the spacer is horizontal (True) or vertical (False)
        fixed_size: Fixed size for the spacer, or None for expanding
        
    Returns:
        QSpacerItem instance
    """
    from PyQt6.QtWidgets import QSpacerItem, QSizePolicy
    
    if fixed_size is not None:
        if horizontal:
            return QSpacerItem(
                fixed_size, 
                0, 
                QSizePolicy.Policy.Fixed, 
                QSizePolicy.Policy.Minimum
            )
        else:
            return QSpacerItem(
                0, 
                fixed_size, 
                QSizePolicy.Policy.Minimum, 
                QSizePolicy.Policy.Fixed
            )
    else:
        if horizontal:
            return QSpacerItem(
                0, 
                0, 
                QSizePolicy.Policy.Expanding, 
                QSizePolicy.Policy.Minimum
            )
        else:
            return QSpacerItem(
                0, 
                0, 
                QSizePolicy.Policy.Minimum, 
                QSizePolicy.Policy.Expanding
            )