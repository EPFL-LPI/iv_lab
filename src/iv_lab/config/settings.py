"""Typed loading of system settings from ``.json`` or ``.toml`` files.

This is the only module in the new package that reads settings files.
All other modules receive the typed settings objects defined here.

The JSON structure, key names, and nesting of the legacy file are preserved
exactly (see ``IVLab/system_settings.json`` and the per-system template
files in ``IVLab/``). During migration every model allows extra fields so
that existing machine configurations keep loading even if they contain keys
that are not mapped yet.

Defaults for optional fields replicate the legacy defaults set in
``IVLab/IVlab.py`` (``system.__init__`` for the ``IVsys`` section and
``SMU.__init__`` for the ``SMU`` section).
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

#: Default settings filename (JSON; TOML is also supported).
DEFAULT_SETTINGS_FILENAME = "system_settings.json"


class LegacyCompatibleModel(BaseModel):
    """Base model that tolerates unmapped legacy keys during migration."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class ComputerSettings(LegacyCompatibleModel):
    """The ``computer`` section."""

    hardware: str
    os: str
    basePath: str
    #: Empty string disables the scrambled duplicate copy and ``ivlablog.txt``.
    sdPath: str


class IVSystemSettings(LegacyCompatibleModel):
    """The ``IVsys`` section."""

    sysName: str
    fullSunReferenceCurrent: float
    calibrationDateTime: str
    referenceDiodeImax: float
    saveDataAutomatic: bool = False
    checkVOCBeforeScan: bool = True
    firstPointDwellTime: float = 5.0
    MPPVoltageStepInitial: float = 0.002
    MPPVoltageStepMax: float = 0.002
    MPPVoltageStepMin: float = 0.001


class LampSettings(LegacyCompatibleModel):
    """The ``lamp`` section.

    ``lightLevelDict`` maps light level in percent of one sun to a
    lamp-type-specific value: a Wavelabs recipe name (str), a filter wheel
    angle (int/float), or a digital filter code (int). JSON only allows
    string keys; they are coerced to float here, as the legacy ``__main__``
    block of ``IVLab/IVlab.py`` does.
    """

    brand: str
    model: str
    emulate: bool
    display_name: Optional[str] = Field(default=None, alias="display name")
    lightLevelDict: Optional[dict[float, Union[int, float, str]]] = None
    visa_address: Optional[str] = None
    visa_library: Optional[str] = None

    @model_validator(mode="after")
    def _apply_legacy_rules(self) -> "LampSettings":
        # Legacy syst_param.__init__ fills in 'display name' if absent.
        if self.display_name is None:
            self.display_name = f"{self.brand} {self.model}"
        # Legacy lamp.__init__ reads lightLevelDict for every brand except
        # 'manual' (case-sensitive comparison, as in the legacy code).
        if self.brand != "manual" and self.lightLevelDict is None:
            raise ValueError(
                f"lamp brand {self.brand!r} requires a 'lightLevelDict' entry"
            )
        return self


class SMUSettings(LegacyCompatibleModel):
    """The ``SMU`` section."""

    brand: str
    model: str
    visa_address: str
    visa_library: str
    emulate: bool
    referenceDiodeSenseMode: str = "2 wire"
    autorange: bool = True
    measSpeed: str = "normal"
    useReferenceDiode: bool = True


class ArduinoSettings(LegacyCompatibleModel):
    """The optional ``arduino`` section (shutter / cell selection)."""

    brand: str
    model: str
    visa_address: str
    visa_library: Optional[str] = None
    emulate: bool = False


class SystemSettings(LegacyCompatibleModel):
    """Top-level model for ``system_settings.json``."""

    computer: ComputerSettings
    IVsys: IVSystemSettings
    lamp: LampSettings
    SMU: SMUSettings
    arduino: Optional[ArduinoSettings] = None


def load_settings(path: Union[str, Path]) -> SystemSettings:
    """Load and validate a system settings file (.json or .toml).

    The file format is detected from the file extension.  Both formats
    produce the same Python dict structure so all Pydantic validation
    applies identically.  ``tomllib`` is part of the Python standard
    library since 3.11.
    """
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".toml":
        raw = tomllib.loads(p.read_text(encoding="utf-8"))
    elif suffix == ".json":
        raw = json.loads(p.read_text(encoding="utf-8"))
    else:
        raise ValueError(
            f"unsupported settings file format {suffix!r} — expected .json or .toml"
        )
    return SystemSettings.model_validate(raw)
