from PyQt5.QtWidgets import QApplication


def app_stylesheet(dark: bool) -> str:
    # Palette
    bg_light = "#ffffff"
    fg_light = "#101014"
    muted_light = "#666a73"

    bg_dark = "#161b22"
    fg_dark = "#e7eaf0"
    muted_dark = "#aab2bf"

    bg = bg_dark if dark else bg_light
    fg = fg_dark if dark else fg_light
    mut = muted_dark if dark else muted_light

    # Surfaces / lines / menus
    surface_low = "#1b2230" if dark else "#f7f8fc"
    surface_mid = "#20283a" if dark else "#ececf4"

    line_dark = "#2a3346" if dark else "#cfd3db"
    line_dark_h = "#323d52" if dark else "#b7bcc7"

    menubar_bg = "#141922" if dark else bg
    menubar_line = "#252c3a" if dark else "#e3e6ee"

    menu_bg = surface_low
    menu_bg_h = surface_mid
    menu_border = line_dark

    # Accents / borders
    accent = "#8aa1ff" if dark else "#cfd3db"
    border_col = line_dark if dark else "#cfd3db"
    border_col_h = line_dark_h if dark else "#b7bcc7"

    # Buttons / nav / write
    primary_bg = "#232b3c" if dark else "#ececf1"
    primary_bg_h = "#3f4d7a" if dark else "#9a96ae"
    primary_bg_d = "2a344a" if dark else "#e6e6f0"
    primary_c = "#ffffff" if dark else "#000000"
    primary_c_d = "#ffffff" if dark else "#8a8a8a"

    nav_bg = "#232b3c" if dark else "#ececf1"
    nav_bg_h = "#2a344a" if dark else "#d9d9e3"
    nav_bg_d = "2a344a" if dark else "#e6e6f0"

    write_bg = "#F7931A"
    write_bg_h = "#FF8C00"
    write_bg_d = "#e6e6f0"

    # Stylesheet
    return f"""
    QWidget {{ background: {bg}; color: {fg}; font-size: 14px; }}
    QLabel {{ color: {fg}; }}

    QMenuBar {{
        background: {menubar_bg};
        color: {fg};
        border-bottom: 1px solid {menubar_line};
        padding: 0 6px;
    }}
    QMenuBar::item {{ padding: 6px 10px; background: transparent; }}
    QMenuBar::item:selected {{ background: {menu_bg_h}; }}

    QMenu {{
        background: {menu_bg};
        color: {fg};
        border: 1px solid {menu_border};
        padding: 6px 4px;
    }}
    QMenu::separator {{ height: 1px; background: {menu_border}; margin: 6px 8px; }}
    QMenu::item {{ padding: 6px 12px; border-radius: 4px; }}
    QMenu::item:selected {{ background: {menu_bg_h}; color: {fg}; }}

    QTabWidget::pane {{ border: 0px; }}
    QTabBar {{ background: transparent; border: 0px; }}
    QTabBar::tab {{
        padding: 8px 12px;
        margin: 2px 0;
        color: {mut};
        background: transparent;
        border: none;
    }}
    QTabBar::tab:selected {{ color: {fg}; font-weight: 600; }}

    QTabWidget#categoryTabs QTabBar {{ background: transparent; qproperty-drawBase: 0; }}
    QTabWidget#categoryTabs QTabBar::tab {{
        border: 1px solid {border_col};
        border-radius: 8px;
        background: {surface_low};
        color: {mut};
        padding: 8px 12px;
        margin: 4px 6px;
        min-width: 150px;
        min-height: 36px;
        text-align: left;
    }}
    QTabWidget#categoryTabs QTabBar::tab:hover {{
        border-color: {border_col_h};
        background: {surface_mid};
        color: {fg};
    }}
    QTabWidget#categoryTabs QTabBar::tab:selected {{
        border-color: {border_col_h};
        background: {nav_bg};
        color: {fg};
        font-weight: 600;
    }}
    QTabWidget#categoryTabs::pane {{ border: 0; border-radius: 8px; margin: 0; }}

    QTabWidget#categoryTabs QTabBar::tab QWidget,
    QTabWidget#categoryTabs QTabBar::tab QLabel,
    QTabWidget#categoryTabs QTabBar::tab QWidget#tabTextLabel {{
        background: transparent;
        border: none;
        color: {mut};
    }}
    QTabWidget#categoryTabs QTabBar::tab:hover QWidget,
    QTabWidget#categoryTabs QTabBar::tab:hover QLabel,
    QTabWidget#categoryTabs QTabBar::tab:hover QWidget#tabTextLabel,
    QTabWidget#categoryTabs QTabBar::tab:selected QWidget,
    QTabWidget#categoryTabs QTabBar::tab:selected QLabel,
    QTabWidget#categoryTabs QTabBar::tab:selected QWidget#tabTextLabel {{
        background: transparent;
        color: {fg};
    }}

    QListWidget, QTreeView, QTableView {{
        background: {bg};
        color: {fg};
        border: 1px solid {border_col};
        border-radius: 8px;
        padding: 4px;
    }}
    QListWidget::item:selected,
    QTreeView::item:selected,
    QTableView::item:selected {{
        background: {nav_bg_h};
        color: {fg};
    }}

    QScrollArea#summaryScroll {{
        background: {bg};
        border: 1px solid {border_col};
        border-radius: 8px;
        padding: 4px;
    }}

    QPushButton {{
        border: 1px solid {border_col};
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 14px;
        background: transparent;
    }}
    QPushButton:hover {{ border-color: {border_col_h}; }}
    QPushButton:focus {{ outline: none; border: 1px solid {accent}; }}
    QPushButton:disabled {{ border-color: {border_col}; color: {mut}; }}

    QPushButton#primaryButton {{ background: {primary_bg}; color: {primary_c}; border-color: {primary_bg_h}; }}
    QPushButton#primaryButton:hover {{ background: {primary_bg_h}; border-color: {primary_bg_h}; }}
    QPushButton#primaryButton:disabled {{ background: {primary_bg_d}; color: {primary_c_d}; border-color: {primary_bg_h}; }}

    QPushButton#navButton {{ background: {nav_bg}; color: {fg}; border-color: {border_col}; }}
    QPushButton#navButton:hover {{ background: {nav_bg_h}; border-color: {border_col_h}; }}
    QPushButton#navButton:disabled {{ background: {nav_bg_d}; color: #707070; border-color: {nav_bg_h}; }}

    QPushButton#WriteButton {{ background: {write_bg}; color: white; font-weight: 600; border-color: {write_bg_h}; }}
    QPushButton#WriteButton:hover {{ background: {write_bg_h}; border-color: {write_bg_h}; }}
    QPushButton#WriteButton:disabled {{ background: {write_bg_d}; color: white; border-color: #9a96ae; }}

    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit, QComboBox {{
        background: {bg};
        color: {fg};
        border: 1px solid {border_col};
        border-radius: 8px;
        padding: 6px 8px;
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTimeEdit:focus,
    QDateTimeEdit:focus, QComboBox:focus {{
        border: 2px solid {accent};
    }}
    QComboBox::drop-down {{
        width: 24px;
        border-left: 1px solid {border_col};
        border-top-right-radius: 8px;
        border-bottom-right-radius: 8px;
    }}
    QComboBox QAbstractItemView {{
        background: {bg};
        color: {fg};
        border: 1px solid {border_col};
        selection-background-color: {nav_bg_h};
        selection-color: {fg};
    }}

    QScrollBar:vertical {{ background: transparent; border: 0; width: 10px; margin: 0; }}
    QScrollBar:horizontal {{ background: transparent; border: 0; height: 10px; margin: 0; }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background: {border_col};
        min-height: 18px;
        min-width: 18px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
        background: {border_col_h};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{ background: transparent; border: 0; height: 0; width: 0; }}

    /* ---------- List rows + checkbox styling for Install/Remove ---------- */

    /* Your custom row: make it visually “transparent” by matching the view bg */
    QWidget#listRow {{
        border: 1px solid {border_col};
        border-radius: 8px;
        background: {bg};     /* was transparent — use {bg} to block bleed */
    }}
    QWidget#listRow:hover {{
        border-color: {border_col_h};
        background: {bg};     /* keep it consistent on hover */
    }}

    /* Checkboxes as primary affordance inside list rows */
    QCheckBox {{
        spacing: 8px;
        padding: 6px 4px;
        font-size: 14px;
        color: {fg};
    }}
    QCheckBox::indicator {{
        width: 18px;
        height: 18px;
        border-radius: 4px;
        border: 2px solid {border_col};
        background: {bg};
        margin-right: 6px;
    }}
    QCheckBox::indicator:hover {{ border-color: {border_col_h}; }}
    QCheckBox::indicator:checked {{
        background: {accent};
        border-color: {accent};
        image: none;
    }}
    QCheckBox::indicator:unchecked {{ image: none; }}
    QCheckBox:disabled, QCheckBox::indicator:disabled {{
        color: {mut};
        border-color: {border_col};
        background: {surface_low};
    }}

    /* Prevent default Qt blue selection highlight on focus or first show */
    QListWidget {{
        selection-background-color: {bg};
        selection-color: {bg};
        show-decoration-selected: 0;   /* also stops “icon area” blue */
    }}

    /* Disable system palette highlight color */
    QListWidget::item,
    QListWidget::item:selected,
    QListWidget::item:selected:active,
    QListWidget::item:selected:!active,
    QListView::item,
    QListView::item:selected,
    QListView::item:selected:active,
    QListView::item:selected:!active {{
        background: {bg};
        color: {bg};
    }}
    """


def apply_theme(app: QApplication, dark: bool) -> None:
    app.setStyleSheet(app_stylesheet(dark))
