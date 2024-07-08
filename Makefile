# Makefile for SAPHanaSR package
# Author: Ilya Manyugin
# License: GPL v 2.0+
# make tarball

FILE_LIST = LICENSE \
		README.md \
        alert \
        crm_cfg \
		icons \
		man \
		ra \
		srHook \
		tools \
		wizard

#TAR_EXTRAS = -X tools/SAPHanaSR-testDriver
TAR_EXTRAS = --exclude="man/*adoc"

PKG = SAPHanaSR-angi
SPECFILE = ${PKG}.spec
VERSION = $(strip $(patsubst Version:,,$(shell grep '^Version:' $(SPECFILE))))

# OBS local project path: set it as a command line argument or as an ENV variable
OBSPROJ ?= "placeholder"
# OBS target platform
OBSTARG ?= "SLE_12_SP2"

tarball:
	@echo -e "\e[33mMaking ${PKG}-${VERSION}.tgz\e[0m"
	tar zcf ${PKG}-${VERSION}.tgz ${TAR_EXTRAS} ${FILE_LIST}
	@echo -e "\e[32mDone\e[0m"

.ONESHELL:
copy: tarball
	
	@if [ $(OBSPROJ) = "placeholder" ]; then
		echo -e "\e[31mProject directory is missing. Set it via 'OBSPROJ=/path/to/project'\e[0m";
		exit 1;
	fi
	@echo -e "\e[33mCopying the SPEC file, CHANGES file and the tarball to ${OBSPROJ}\e[0m"
	@cp ${PKG}.changes ${OBSPROJ}
	@cp ${PKG}.spec ${OBSPROJ}
	@cp ${PKG}-${VERSION}.tgz ${OBSPROJ}
	@echo -e "\e[32mDone\e[0m"

.ONESHELL:
build: copy
	@echo -e "\e[33mInitiating the build\e[0m"
	@cd ${OBSPROJ}
	osc -A https://api.suse.de build ${OBSTARG}
	@echo -e "\e[32mDone\e[0m"


.ONESHELL:
commit: copy
	@echo -e "\e[33mCommiting the code\e[0m"
	@cd ${OBSPROJ}
	osc -A https://api.suse.de addremove
	osc -A https://api.suse.de commit
	@echo -e "\e[32mDone\e[0m"

.phony: 	tarball

.PHONY: checkstyle
checkstyle:
ifneq ($(CHECKSTYLE),0)
	find . -type f -exec awk ' /^#!.*bash/{print FILENAME} {nextfile}' {} + | xargs shellcheck -s bash || :
	find . -type f -exec awk ' /^#!.*perl/{print FILENAME} {nextfile}' {} + | grep -v .git | xargs perlcritic --gentle || :
	find . -name '*.py' | xargs flake8 --ignore=E501 || :
endif

PHONY: test
test: checkstyle
