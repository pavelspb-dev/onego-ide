%define _name onego-ide
%define _version 1.0
%define _release alt1

Name:           %{_name}
Version:        %{_version}
Release:        %{_release}
Summary:        Onego-15VA educational emulator+assembler+IDE
License:        MIT
Group:          Education
Url:            https://github.com/pavelspb-dev/onego-ide
Source0:        %{name}-%{version}.tar.gz
Source1:        onego-ide.desktop
Source2:        onego-ide.png
BuildArch:      noarch

Requires:       python3
Requires:       python3-module-PyQt5

%description
Onego-15VA educational assembler IDE with interactive lessons,
code editor and Onego-15VA emulator.

%prep
%setup -q

%install
mkdir -p %{buildroot}%{_datadir}/%{name}
cp -r *.py %{buildroot}%{_datadir}/%{name}/

mkdir -p %{buildroot}%{_bindir}
cat > %{buildroot}%{_bindir}/%{name} <<EOF
#!/bin/bash
exec -a onego-ide python3 %{_datadir}/%{name}/onegoide.py "\$@"
EOF
chmod 755 %{buildroot}%{_bindir}/%{name}

install -Dpm 0644 %{SOURCE1} %{buildroot}%{_datadir}/applications/%{name}.desktop
install -Dpm 0644 %{SOURCE2} %{buildroot}%{_datadir}/icons/hicolor/48x48/apps/%{name}.png

%files
%{_bindir}/%{name}
%dir %{_datadir}/%{name}
%{_datadir}/%{name}/*.py
%{_datadir}/applications/%{name}.desktop
%{_datadir}/icons/hicolor/48x48/apps/%{name}.png

%changelog
* Thu Sep 10 2026 PavelSpbDev <pavelspb-dev@mail.ru> 1.0-alt1
- Initial build
