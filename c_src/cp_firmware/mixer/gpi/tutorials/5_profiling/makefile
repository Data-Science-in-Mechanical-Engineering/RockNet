
### Project files and settings

PROJECT                 = test
TARGETS                 = hex

LIBDIR					= ..
SOURCEDIRS              = . $(LIBDIR)
INCLUDEDIRS             = $(SOURCEDIRS)

SOURCEFILES             = main.c
SOURCEFILES_LIB         = $(LIBDIR)/gpi/gpi.c

# override DEFINES += "GPI_TRACE_BASE_SELECTION=GPI_TRACE_LOG_SCOPE|GPI_TRACE_LOG_TIME|GPI_TRACE_LOG_TYPE|GPI_TRACE_LOG_PROGRAM_FLOW"

# ifeq (,${findstring MX_CONFIG_FILE,$(DEFINES)})
#   override DEFINES += MX_CONFIG_FILE=config.h
# endif

ifeq (,${findstring GPI_TRACE_MODE,$(DEFINES)})
  override DEFINES += GPI_TRACE_MODE=GPI_TRACE_MODE_TRACE
  # override DEFINES += GPI_TRACE_MODE=GPI_TRACE_MODE_NO_TRACE
endif


### Tools

CC       = msp430-gcc
LD       = msp430-gcc
AS       = msp430-as
AR       = msp430-ar
NM       = msp430-nm
OBJCOPY  = msp430-objcopy
OBJDUMP  = msp430-objdump
SIZE     = msp430-size
STRIP    = msp430-strip
BSL      = msp430-bsl
BASE64   = base64

## check compiler version
## this requirement may be relaxed in future releases
#ifeq (,${shell $(CC) --version | grep 4.6.3})
#  ${error unsupported version of $(CC) (required: 4.6.3, current: ${shell $(CC) --version | grep GCC})}
#endif


### Flags

MCU      = msp430f1611

CFLAGS   = -mmcu=$(MCU) -Wall -g -Os -ffunction-sections -fdata-sections
LDFLAGS  = -mmcu=$(MCU) -Wl,-Map=$(PROJECT).map -Wl,-gc-sections -Wl,--script=profile.ld
# -Werror

### Target definitions

.DEFAULT_GOAL := ${firstword $(TARGETS)}

ifeq ($(TARGET),)
  TARGET = ${filter $(TARGETS),$(MAKECMDGOALS)}
  ifeq ($(TARGET),)
    TARGET = $(.DEFAULT_GOAL)
    ${info TARGET not specified, using default (TARGET = $(TARGET))}
  else ifneq (${words $(TARGET)},1)
    ${error TARGET definition is ambigous, please specify one target at a time}
  endif
endif

#CFLAGS += -D$(TARGET)
ifeq ($(TARGET),hex)
  CFLAGS += -DGPI_ARCH_PLATFORM=GPI_ARCH_BOARD_TMOTE
else ifeq (,${findstring GPI_ARCH_PLATFORM,$(DEFINES)})
  ${warning GPI_ARCH_PLATFORM not defined}
endif

OBJECTDIR = obj_$(TARGET)
ifeq (${wildcard $(OBJECTDIR)},)
  DUMMY := ${shell mkdir $(OBJECTDIR)}
endif

### Paths, defines and so on

COMMA		:= ,
FRPATHSEP	:= __
FRUP		:= ~

flatten		= ${subst ..,$(FRUP),${subst /,$(FRPATHSEP),$(1)}}
unflatten	= ${subst $(FRUP),..,${subst $(FRPATHSEP),/,$(1)}}

oname		= ${call flatten, ${patsubst %.c,%.o,${patsubst %.S,%.o,$(1)}}}

OBJECTFILES      = ${addprefix $(OBJECTDIR)/,${call oname, $(SOURCEFILES)}}
OBJECTFILES_LIB  = ${addprefix $(OBJECTDIR)/,${call oname, $(SOURCEFILES_LIB)}}
OBJECTLIB        = ${addprefix $(OBJECTDIR)/,$(PROJECT)-lib.a}

vpath %.c $(SOURCEDIRS)
#vpath %.S $(SOURCEDIRS)

CFLAGS += ${addprefix -D,${subst $(COMMA), ,$(DEFINES)}}
CFLAGS += ${addprefix -I,$(INCLUDEDIRS)}

### Automatic dependency generation
### For details see http://make.mad-scientist.net/papers/advanced-auto-dependency-generation/#combine

ifneq ($(MAKECMDGOALS),clean)
  -include ${addprefix $(OBJECTDIR)/,${call flatten,$(SOURCEFILES:.c=.d) $(SOURCEFILES_LIB:.c=.d)}}
endif

define FINALIZE_DEPENDENCY
# add a rule for the source file (this is helpful for source collection)
  echo >> $(@:.o=.d);	\
  cp $(@:.o=.d) $(@:.o=.$$$$); \
  sed -e ':a;N;$$!ba;s/[\\]\n//g' < $(@:.o=.$$$$) | \
  sed -E -e '/^\s*$$/ q' -e 's/[^:]+.o\s*:\s*(\S+)/\1:/' >> $(@:.o=.d); \
  rm -f $(@:.o=.$$$$); \
  touch $@
endef

### Build rules

.PHONY: usage clean all $(TARGETS)

.SUFFIXES:

usage:
	@echo
	@echo "make <goal(s) and/or target> [TARGET=<target>] [DEFINES=<defines>]"

clean:
	-rm -rf $(OBJECTDIR)
ifeq ($(TARGET),hex)
	-rm -f $(PROJECT).sky $(PROJECT).hex $(PROJECT).lst $(PROJECT).map
# else ifeq ($(TARGET),FLOCKLAB)
# 	-rm -f $(PROJECT)_flocklab.xml
#else ifeq ($(TARGET),INDRIYA)
endif

#all: $(TARGETS)

# %.o : %.c
# Unfortunately we cannot write a rule like this:
#	$(OBJECTDIR)/%.o: ${call unflatten,%.c}
#		...
# because the function call in prerequisites does not get resolved.
# Therefore we use an intermediate eval step to generate explicit rules.
define orule =
$(1:.o=.d) : ;
$(1) : ${call unflatten, $(basename $(notdir $(1))).c} $(1:.o=.d)
#	@echo orule $$@ : $$^
	$$(CC) $$(CFLAGS) -MMD -MP -c $$< -o $$@
	@$$(FINALIZE_DEPENDENCY)
endef
$(foreach obj,$(OBJECTFILES) $(OBJECTFILES_LIB),$(eval $(call orule,$(obj))))

$(OBJECTLIB): $(OBJECTFILES_LIB)
	$(AR) rcf $@ $^

$(OBJECTDIR)/$(PROJECT).sky: $(OBJECTFILES) $(OBJECTLIB)
	$(LD) $(LDFLAGS) ${filter-out %.a,$^} ${filter %.a,$^} -o $@
	$(OBJDUMP) -t -d -S $@ > $(PROJECT).lst
	$(OBJDUMP) -s -j .data -j .rodata $@ >> $(PROJECT).lst
	@echo
	@$(SIZE) $@
	@echo

hex: $(OBJECTDIR)/$(PROJECT).sky
	$(OBJCOPY) -O ihex $< $(PROJECT).hex

# FLOCKLAB: $(PROJECT)_flocklab.xml

# $(PROJECT)_flocklab.xml : $(OBJECTDIR)/$(PROJECT).sky config_flocklab.xml
# 	@echo
# 	@echo FlockLab postprocessing...
# 	@echo
# 	@rm -f $(OBJECTDIR)/src.d
# 	@echo flocklab_src__2 : > $(OBJECTDIR)/src.lst
# 	@$(MAKE) --no-print-directory TARGET=$(TARGET) flocklab_src__1
# 	@$(MAKE) --no-print-directory TARGET=$(TARGET) flocklab_src__2
# 	tar -z -cf $(OBJECTDIR)/$(PROJECT)-source.tar.gz -T $(OBJECTDIR)/src.lst
# 	@echo openssl $(OBJECTDIR)/$(PROJECT)-source.tar.gz ">" $(OBJECTDIR)/$(PROJECT)-source.enc
# 	@openssl enc -aes-256-cbc -e -pass pass:$(PROJECT) -in $(OBJECTDIR)/$(PROJECT)-source.tar.gz -out $(OBJECTDIR)/$(PROJECT)-source.enc
# 	$(OBJCOPY) --add-section conf=$(OBJECTDIR)/$(PROJECT)-source.enc $< $(<:.sky=_flocklab.sky)
# 	@rm -f $(<:.sky=_flocklab.b64)
# 	$(BASE64) $(<:.sky=_flocklab.sky) > $(<:.sky=_flocklab.b64)
# 	$(CC) -E -x c -P -C -I$(OBJECTDIR) -DIMAGE=$(<:.sky=_flocklab.b64) -o $(PROJECT)_flocklab.xml config_flocklab.xml
#
# # include internal sub-targets only when necessary
# ifeq (flocklab_src,${firstword ${subst __, ,$(MAKECMDGOALS)}})
#
#   -include $(OBJECTDIR)/src.d
#
#   flocklab_src__1 : ${patsubst %,$(OBJECTDIR)/src/%,${call flatten,$(SOURCEFILES) $(SOURCEFILES_LIB)}}
# 	@tr -s -t "\n" " " < $(OBJECTDIR)/src.lst > $(OBJECTDIR)/src.d
#
#   define srule =
#   $(OBJECTDIR)/src/${call flatten,$(1)} : $(1) ;
#   .PHONY: $(1)
#   $(1) :
# 	@echo $$@ $$^ >> $(OBJECTDIR)/src.lst
#   endef
#   ${foreach src,$(SOURCEFILES) $(SOURCEFILES_LIB), ${eval ${call srule,$(src)}}}
#
#   flocklab_src__2 :
# 	@echo $^ > $(OBJECTDIR)/src.d
# 	@tr -s -t " \t" "\n" < $(OBJECTDIR)/src.d > $(OBJECTDIR)/src.lst
#
# endif
