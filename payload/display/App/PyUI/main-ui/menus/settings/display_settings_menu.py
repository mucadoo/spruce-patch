
from controller.controller_inputs import ControllerInput
from devices.device import Device
from menus.settings import settings_menu
from views.grid_or_list_entry import GridOrListEntry


from menus.language.language import Language

class DisplaySettingsMenu(settings_menu.SettingsMenu):
    def __init__(self):
        super().__init__()
    
    def brightness_adjust(self, input: ControllerInput):
        if(ControllerInput.DPAD_LEFT == input or ControllerInput.L1 == input):
            Device.get_device().lower_brightness()
        elif(ControllerInput.DPAD_RIGHT == input or ControllerInput.R1 == input):
            Device.get_device().raise_brightness()

    def contrast_adjust(self, input: ControllerInput):
        if(ControllerInput.DPAD_LEFT == input or ControllerInput.L1 == input):
            Device.get_device().lower_contrast()
        elif(ControllerInput.DPAD_RIGHT == input or ControllerInput.R1 == input):
            Device.get_device().raise_contrast()

    def saturation_adjust(self, input: ControllerInput):
        if(ControllerInput.DPAD_LEFT == input or ControllerInput.L1 == input):
            Device.get_device().lower_saturation()
        elif(ControllerInput.DPAD_RIGHT == input or ControllerInput.R1 == input):
            Device.get_device().raise_saturation()
    
    def lumination_adjust(self, input: ControllerInput):
        if(ControllerInput.DPAD_LEFT == input or ControllerInput.L1 == input):
            Device.get_device().lower_lumination()
        elif(ControllerInput.DPAD_RIGHT == input or ControllerInput.R1 == input):
            Device.get_device().raise_lumination()
    
    def hue_adjust(self, input: ControllerInput):
        if(ControllerInput.DPAD_LEFT == input or ControllerInput.L1 == input):
            Device.get_device().lower_hue()
        elif(ControllerInput.DPAD_RIGHT == input or ControllerInput.R1 == input):
            Device.get_device().raise_hue()

    # Stock Flip values from devices/miyoo/flip/flip-system.json.
    DEFAULT_DISPLAY = {"backlight": 10, "brightness": 7, "contrast": 10, "saturation": 14, "hue": 10}
    # Lowest lamp step that stays lit, with brightness 8 and contrast 2.
    DIMMEST_DISPLAY = {"backlight": 0, "brightness": 8, "contrast": 2}

    def _apply_display(self, levels):
        device = Device.get_device()
        cfg = device.system_config
        cfg.reload_config()
        applied = []
        if "backlight" in levels and hasattr(device, "_set_lumination_to_config"):
            cfg.set_backlight(levels["backlight"])
            applied.append(device._set_lumination_to_config)
        if "brightness" in levels and device.supports_brightness_calibration() and hasattr(device, "_set_brightness_to_config"):
            cfg.set_brightness(levels["brightness"])
            applied.append(device._set_brightness_to_config)
        if "contrast" in levels and device.supports_contrast_calibration() and hasattr(device, "_set_contrast_to_config"):
            cfg.set_contrast(levels["contrast"])
            applied.append(device._set_contrast_to_config)
        if "saturation" in levels and device.supports_saturation_calibration() and hasattr(device, "_set_saturation_to_config"):
            cfg.set_saturation(levels["saturation"])
            applied.append(device._set_saturation_to_config)
        if "hue" in levels and device.supports_hue_calibration() and hasattr(device, "_set_hue_to_config"):
            cfg.set_hue(levels["hue"])
            applied.append(device._set_hue_to_config)
        cfg.save_config()
        for apply in applied:
            apply()

    def apply_default_display(self, input: ControllerInput):
        if ControllerInput.A == input:
            self._apply_display(self.DEFAULT_DISPLAY)

    def apply_dimmest_display(self, input: ControllerInput):
        if ControllerInput.A == input:
            self._apply_display(self.DIMMEST_DISPLAY)

    def adjust_rgb(self, input: ControllerInput, getter, setter):
        delta = 0
        if(ControllerInput.DPAD_LEFT == input):
            delta = -1
        elif(ControllerInput.L1== input):
            delta = -10
        elif(ControllerInput.DPAD_RIGHT == input):
            delta = +1
        elif(ControllerInput.R1 == input):
            delta = +10

        new_value = getter() + delta
        if(new_value < 0): 
            new_value = 255
        elif(new_value > 255): 
            new_value = 0
        
        setter(new_value)
            
    def build_options_list(self):
        option_list = []

        option_list.append(
                GridOrListEntry(
                        primary_text="Default",
                        value_text=None,
                        image_path=None,
                        image_path_selected=None,
                        description="Backlight 10, brightness 7, contrast 10, saturation 14, hue 10",
                        icon=None,
                        value=self.apply_default_display
                    )
            )
        option_list.append(
                GridOrListEntry(
                        primary_text="Dimmest",
                        value_text=None,
                        image_path=None,
                        image_path_selected=None,
                        description="Lowest lit backlight, brightness 8, contrast 2. Saturation and hue stay as they are.",
                        icon=None,
                        value=self.apply_dimmest_display
                    )
            )

        option_list.append(
                GridOrListEntry(
                        primary_text=Language.backlight(),
                        value_text="<    " + str(Device.get_device().lumination()) + "    >",
                        image_path=None,
                        image_path_selected=None,
                        description=None,
                        icon=None,
                        value=self.lumination_adjust
                    )
            )

        if(Device.get_device().supports_brightness_calibration()):
            option_list.append(
                    GridOrListEntry(
                            primary_text=Language.brightness(),
                            value_text="<    " + str(Device.get_device().brightness()) + "    >",
                            image_path=None,
                            image_path_selected=None,
                            description=None,
                            icon=None,
                            value=self.brightness_adjust
                        )
                )
        if(Device.get_device().supports_contrast_calibration()):
            option_list.append(
                    GridOrListEntry(
                            primary_text=Language.contrast(),
                            value_text="<    " + str(Device.get_device().contrast()) + "    >",
                            image_path=None,
                            image_path_selected=None,
                            description=None,
                            icon=None,
                            value=self.contrast_adjust
                        )
                )
        if(Device.get_device().supports_saturation_calibration()):
            option_list.append(
                    GridOrListEntry(
                            primary_text=Language.saturation(),
                            value_text="<    " + str(Device.get_device().saturation()) + "    >",
                            image_path=None,
                            image_path_selected=None,
                            description=None,
                            icon=None,
                            value=self.saturation_adjust
                        )
                )          
        
        if(Device.get_device().supports_hue_calibration()):
            option_list.append(
                    GridOrListEntry(
                            primary_text=Language.hue(),
                            value_text="<    " + str(Device.get_device().hue()) + "    >",
                            image_path=None,
                            image_path_selected=None,
                            description=None,
                            icon=None,
                            value=self.hue_adjust
                        )
                )          
        
        if(Device.get_device().supports_rgb_calibration()):
            option_list.append(
                    GridOrListEntry(
                            primary_text=Language.red(),
                            value_text="<    " + str(Device.get_device().get_disp_red()) + "    >",
                            image_path=None,
                            image_path_selected=None,
                            description=None,
                            icon=None,
                            value=lambda input_value, getter=Device.get_device().get_disp_red, setter=Device.get_device().set_disp_red: self.adjust_rgb(input_value,getter,setter)
                        )
                )          
            option_list.append(
                    GridOrListEntry(
                            primary_text=Language.blue(),
                            value_text="<    " + str(Device.get_device().get_disp_blue()) + "    >",
                            image_path=None,
                            image_path_selected=None,
                            description=None,
                            icon=None,
                            value=lambda input_value, getter=Device.get_device().get_disp_blue, setter=Device.get_device().set_disp_blue: self.adjust_rgb(input_value,getter,setter)
                        )
                )          
            option_list.append(
                    GridOrListEntry(
                            primary_text=Language.green(),
                            value_text="<    " + str(Device.get_device().get_disp_green()) + "    >",
                            image_path=None,
                            image_path_selected=None,
                            description=None,
                            icon=None,
                            value=lambda input_value, getter=Device.get_device().get_disp_green, setter=Device.get_device().set_disp_green: self.adjust_rgb(input_value,getter,setter)
                        )
                )          
        
        return option_list
