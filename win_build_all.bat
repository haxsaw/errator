rem make the output wheels directory and clean of previous builds
mkdir wheels
del wheels\*.whl
rem this is the base directory where all the python installs can be found
set PREFIX=c:\py
rem this is the base directory where the build/test virtualenvs will be made
set VPY_ROOT=c:\vpy
rem the build virtualenv
set BUILD=%VPY_ROOT%\err_build
rem the test virtualenv
set TEST=%VPY_ROOT%\err_test
rem all of the available Python releases
set PYPATH=%PREFIX%\py36 %PREFIX%\py37 %PREFIX%\py38 %PREFIX%\py39

echo %PREFIX%, %VPY_ROOT%, %BUILD%, %TEST%
for %%P in (%PYPATH%) do (
    echo %%P
    rem remove previous files
    rd /s /q %BUILD%
    rd /s /q %TEST%
    rem upgrade pip in the version install & install the build tools
    %%P\Scripts\python.exe -m pip install --upgrade pip
    %%P\Scripts\pip install virtualenv
    rem build out and activate the virtualenv for the py version
    %%P\Scripts\virtualenv -p %%P\python.exe %BUILD%
    %BUILD%\Scripts\activate.bat
    rem install the build tools in the build virtualenv & build
    %BUILD%\Scripts\pip install wheel
    %BUILD%\Scripts\pip install -r requirements.txt
    %BUILD%\Scripts\pip wheel . --no-deps -w wheels
    deactivate
    rem now make the test environment
    %%P\Scripts\virtualenv -p %%P\python.exe %TEST%
    rem activate and install the new package into test
    %TEST%\Scripts\activate.bat
    %TEST%\Scripts\pip install errator -f wheels
    %TEST%\Scripts\pip install pytest
    rem test the install
    %TEST%\Scripts\pytest tests.py
    deactivate
)
rem final cleanup
rd /s /q %BUILD%
rd /s /q %TEST%


