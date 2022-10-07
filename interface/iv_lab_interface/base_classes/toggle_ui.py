class ToggleUiInterface():
    def toggle_ui(self, enable: bool = True):
        """
        Enable or disable UI elements.

        :param enable: Whether to enable or disable elements.
            [Default: True]
        """
        if enable:
            self.enable_ui()

        else:
            self.disable_ui()

    def enable_ui(self):
        """
        Enable UI elements.
        """
        raise NotImplementedError()
    
    def disable_ui(self):
        """
        Disable UI elements.
        """
        raise NotImplementedError()

