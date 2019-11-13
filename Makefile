# Makefile for SAPHanaSR package
# Author: Ilya Manyugin
# License: GPL v 2.0+
# make REL=12 tarball
# make REL=15 tarball

FILE_LIST = doc \
			man \
			ra \
	 		test \
			icons \
			srHook \
	 		wizard 

TAR_EXTRAS = -X test/SAPHanaSR-testDriver

PKG = SAPHanaSR
SPECFILE = ${PKG}.spec
CHANGESFILE = ${PKG}.changes
VERSION = $(strip $(patsubst Version:,,$(shell grep '^Version:' $(SPECFILE))))

# OBS local project path: set it as a command line argument or as an ENV variable
OBSPROJ ?= "placeholder"
# OBS target platform
OBSTARG ?= "SLE_12_SP2"

ifeq ($(REL),)
$(info REL is empty)
else
$(info REL is $(REL))
endif

tarball:
	@echo -e "\e[33mMaking ${PKG}-${VERSION}.tgz\e[0m"
	tar zcf ${PKG}-${VERSION}.tgz ${FILE_LIST} ${TAR_EXTRAS}
	@echo -e "\e[32mDone\e[0m"

.ONESHELL:
copy: tarball
	
	@if [ -z "$(REL)" ]; then
		echo -e "\e[31m REL is empty. Set it via 'REL=12' or 'REL=15'\e[0m";
		exit 1;
	fi
	@cp ${PKG}.changes_$(REL) ${CHANGESFILE}
	@if [ $(OBSPROJ) = "placeholder" ]; then
		echo -e "\e[31mProject directory is missing. Set it via 'OBSPROJ=/path/to/project'\e[0m";
		exit 1;
	fi
	@echo -e "\e[33mCopying the SPEC file, CHANGES file and the tarball to ${OBSPROJ}\e[0m"
	@cp SAPHanaSR.changes ${OBSPROJ}
	@cp SAPHanaSR.spec ${OBSPROJ}
	@cp SAPHanaSR-${VERSION}.tgz ${OBSPROJ}
	@rm ${CHANGESFILE}
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
