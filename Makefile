SRCDIR=src

SCRIPTS=src/ganglia_parser
PLUGINS=src/check_ganglios_disk src/check_ganglios_generic_value src/check_ganglios_diskio  src/check_ganglios_memory_v2
MODULES=src/ganglios/__init__.py src/ganglios/ganglios.py

all:

install:
	install -d ${DESTDIR}/usr/sbin
	install -m 0755 ${SCRIPTS} ${DESTDIR}/usr/sbin
	
	install -d ${DESTDIR}/usr/lib/nagios/plugins
	install -m 0755 ${PLUGINS} ${DESTDIR}/usr/lib/nagios/plugins
	
	install -d ${DESTDIR}/usr/share/pyshared/ganglios
	install -m 0644 ${MODULES} ${DESTDIR}/usr/share/pyshared/ganglios
	
	install -d ${DESTDIR}/var/lib/ganglia/xmlcache
	install -d ${DESTDIR}/var/log/ganglia

clean:

deb:
	debuild -uc -us -i -b

source-deb:
	debuild -uc -us -i -S
	
debclean:
	debuild clean
