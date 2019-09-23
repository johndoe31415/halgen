#	halgen - HAL generator for different microcontrollers
#	Copyright (C) 2012-2019 Johannes Bauer
#
#	This file is part of halgen.
#
#	halgen is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	halgen is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with halgen; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>

import uuid
import time

from Traits import Traits
from XMLParser import XMLException

class HALGenerator():
	PINTYPE_IN = 0
	PINTYPE_OUT = 1
	PINTYPE_IO = 2

	VAL_LOW = 0
	VAL_HIGH = 1
	VAL_INACTIVE = 2
	VAL_ACTIVE = 3

	def __init__(self, xml, options):
		self.__xml = xml
		self.__options = options
		self.__initializers = [ ]
		self.__f = None
		self.__portpins = { }
		self.__portnames = set()

	def __outputline(self, line = ""):
		self.__f.write(line + "\n")

	def __outputsymbol(self, complete_name, key, value):
		if complete_name is not None:
			key = key.replace("#", complete_name)
			value = value.replace("#", complete_name)
		self.__f.write("#define %-40s %s\n" % (key, value))

	def __outputmocksymbol(self, complete_name, key, returns = None):
		if returns is None:
			value = "fprintf(stderr, \"Mock HAL: %s\\n\")" % (key);
		else:
			value = "fprintf(stderr, \"Mock HAL: %s\\n\"), %s" % (key, returns);
		self.__outputsymbol(complete_name, key, value)

	def __parse_pintype(self, value):
		value = value.lower()
		if value in [ "i", "in", "input" ]:
			return HALGenerator.PINTYPE_IN
		elif value in [ "o", "out", "output" ]:
			return HALGenerator.PINTYPE_OUT
		elif value in [ "io", "inout" ]:
			return HALGenerator.PINTYPE_IO
		else:
			raise Exception("%s is not a valid pintype." % (value))

	def __parse_act(self, value):
		value = value.lower()
		if value in [ "off", "inactive", "false" ]:
			return HALGenerator.VAL_INACTIVE
		elif value in [ "on", "active", "true" ]:
			return HALGenerator.VAL_ACTIVE
		else:
			raise Exception("%s is not a valid activity type." % (value))

	def __parse_lhact(self, value):
		value = value.lower()
		if value in [ "off", "inactive", "false" ]:
			return HALGenerator.VAL_INACTIVE
		elif value in [ "on", "active", "true" ]:
			return HALGenerator.VAL_ACTIVE
		elif value in [ "low", "l" ]:
			return HALGenerator.VAL_LOW
		elif value in [ "high", "h" ]:
			return HALGenerator.VAL_HIGH
		else:
			raise Exception("%s is not a valid activity/lowhigh type." % (value))

	def __gen_single_portpin(self, portpin, name, description, ppuuid):
		initialname = name

		while name[0] == "*":
			print(self.__xml)
			routenode = XMLTool.findnode(self.__xml, "/*/route[@alias=\"%s\"]" % (name))
			self.__outputline("/* Route %s -> %s */" % (name, routenode["dest"]))
			name = routenode["dest"]

		if name != initialname:
			self.__outputline("/* Final route %s -> %s */" % (initialname, name))

		portid = name[1]
		portpinno = int(name[2])
		portident = (portid, portpinno)
		if (portident in self.__portpins) and (self.__portpins[portident] != ppuuid):
			raise Exception("Duplicate definition of portpin %s%d, use also requested for '%s'." % (portident[0], portident[1], description))
		else:
			self.__portpins[portident] = ppuuid

		if description in self.__portnames:
			raise Exception("Duplicate definition of portpin name %s, use also requested for %s%d." % (description, portident[0], portident[1]))
		self.__portnames.add(description)

		templatename = portpin.get("template")
		if templatename is not None:
			# Find template node
			templatenode = self.__xml.searchunique("template", name = templatename)
		else:
			templatenode = None

		def getfallbacknode(portpin, templatenode, itemname):
			chld = portpin.getchild(itemname)
			if (chld is None) and (templatenode is not None):
				chld = templatenode.getchild(itemname)
			return chld

		pin = getfallbacknode(portpin, templatenode, "pin")
		if pin is None:
			raise Exception("%s has no 'pin' item set" % (portpin))
		prefix = getfallbacknode(portpin, templatenode, "prefix")
		activelow = getfallbacknode(portpin, templatenode, "activelow") is not None

		pininitvalue = None
		pininitpullup = None
		pininitstate = None
		pintype = self.__parse_pintype(pin["type"])
		if pintype == HALGenerator.PINTYPE_IN:
			pininitpullup = self.__parse_act(pin["initialpullup"])
		elif pintype == HALGenerator.PINTYPE_OUT:
			pininitvalue = self.__parse_lhact(pin["initialvalue"])
		elif pintype == HALGenerator.PINTYPE_IO:
			pininitstate = self.__parse_pintype(pin["initialstate"])
			if pininitstate == HALGenerator.PINTYPE_IN:
				pininitpullup = self.__parse_act(pin["initialpullup"])
			elif pininitstate == HALGenerator.PINTYPE_OUT:
				pininitvalue = self.__parse_lhact(pin["initialvalue"])
			else:
				raise Exception("Initial state of a inout-pin cannot be inout, but must be either 'input' OR 'output'.");

		if prefix is not None:
			complete_name = "%s_%s" % (prefix["value"], description)
		else:
			complete_name = description

		commentflags = [ ]
		if pintype == HALGenerator.PINTYPE_IN:
			commentflags.append("Input")
		elif pintype == HALGenerator.PINTYPE_OUT:
			commentflags.append("Output")
		elif pintype == HALGenerator.PINTYPE_IO:
			commentflags.append("Input/Output")
			if pininitstate == HALGenerator.PINTYPE_IN:
				commentflags.append("Initially Input")
			elif pininitstate == HALGenerator.PINTYPE_OUT:
				commentflags.append("Initially Output")

		if pininitvalue == HALGenerator.VAL_LOW:
			commentflags.append("Initially LOW")
		elif pininitvalue == HALGenerator.VAL_HIGH:
			commentflags.append("Initially HIGH")
		elif pininitvalue == HALGenerator.VAL_ACTIVE:
			commentflags.append("Initially Active")
		elif pininitvalue == HALGenerator.VAL_INACTIVE:
			commentflags.append("Initially Inactive")

		if pininitpullup == HALGenerator.VAL_ACTIVE:
			commentflags.append("Initially Pullup On")
		elif pininitpullup == HALGenerator.VAL_INACTIVE:
			commentflags.append("Initially Pullup Off")

		if activelow:
			commentflags.append("Active-Low")

		self.__outputline("/* %s -> %s (%s) */" % (complete_name, name, ", ".join(commentflags)))

		if self.__traits.arch in [ Traits.TRAIT_ARCH_AVR, Traits.TRAIT_ARCH_I686 ]:
			self.__outputsymbol(complete_name, "#_BIT", str(portpinno))
			self.__outputsymbol(complete_name, "#_PIN", "PIN" + portid)
			self.__outputsymbol(complete_name, "#_PORT", "PORT" + portid)
			self.__outputsymbol(complete_name, "#_DDR", "DDR" + portid)
		elif self.__traits.arch == Traits.TRAIT_ARCH_XMEGA:
			self.__outputsymbol(complete_name, "#_BIT", str(portpinno))
			self.__outputsymbol(complete_name, "#_PIN", "PORT" + portid + ".IN")
			self.__outputsymbol(complete_name, "#_PORT", "PORT" + portid + ".OUT")
			self.__outputsymbol(complete_name, "#_DDR", "PORT" + portid + ".DIR")

		if pintype in [ HALGenerator.PINTYPE_IN, HALGenerator.PINTYPE_IO ]:
			if self.__traits.arch in [ Traits.TRAIT_ARCH_AVR, Traits.TRAIT_ARCH_XMEGA ]:
				self.__outputsymbol(complete_name, "#_SetPullupActive()", "#_PORT |= _BV(#_BIT)")
				self.__outputsymbol(complete_name, "#_SetPullupInactive()", "#_PORT &= ~_BV(#_BIT)")
				self.__outputsymbol(complete_name, "#_ModeInput()", "#_DDR &= ~_BV(#_BIT)")
				self.__outputsymbol(complete_name, "#_IsInput()", "((#_DDR & _BV(#_BIT)) == 0)")
				self.__outputsymbol(complete_name, "#_Get()", "(#_PIN & _BV(#_BIT))")
			elif self.__traits.arch == Traits.TRAIT_ARCH_I686:
				self.__outputmocksymbol(complete_name, "#_SetPullupActive()")
				self.__outputmocksymbol(complete_name, "#_SetPullupInactive()")
				self.__outputmocksymbol(complete_name, "#_ModeInput()")
				self.__outputmocksymbol(complete_name, "#_Get()", "0")

			self.__outputsymbol(complete_name, "#_GetBit()", "(#_Get() >> #_BIT)")

		if pintype in [ HALGenerator.PINTYPE_OUT, HALGenerator.PINTYPE_IO ]:
			if self.__traits.arch in [ Traits.TRAIT_ARCH_AVR, Traits.TRAIT_ARCH_XMEGA ]:
				self.__outputsymbol(complete_name, "#_ModeOutput()", "#_DDR |= _BV(#_BIT)")
				self.__outputsymbol(complete_name, "#_IsOutput()", "((#_DDR & _BV(#_BIT)) != 0)")
				self.__outputsymbol(complete_name, "#_SetHIGH()", "#_PORT |= _BV(#_BIT)")
				self.__outputsymbol(complete_name, "#_SetLOW()", "#_PORT &= ~_BV(#_BIT)")
				self.__outputsymbol(complete_name, "#_Get()", "(#_PIN & _BV(#_BIT))")
			elif self.__traits.arch == Traits.TRAIT_ARCH_I686:
				self.__outputmocksymbol(complete_name, "#_ModeOutput()")
				self.__outputmocksymbol(complete_name, "#_SetHIGH()")
				self.__outputmocksymbol(complete_name, "#_SetLOW()")
				self.__outputsymbol(complete_name, "#_Get()", "(#_PIN & _BV(#_BIT))")

			a = [ "LOW", "HIGH"	]
			if activelow: a.reverse()
			self.__outputsymbol(complete_name, "#_SetInactive()", "#_Set%s()" % (a[0]))
			self.__outputsymbol(complete_name, "#_SetActive()", "#_Set%s()" % (a[1]))
			self.__outputsymbol(complete_name, "#_Toggle()", "#_PORT ^= _BV(#_BIT)")
			self.__outputsymbol(complete_name, "#_SetConditional(condition)", "if (condition) #_SetActive(); else #_SetInactive()")
			self.__outputsymbol(complete_name, "#_SetConditionalToggle(conditionon, conditionoff, conditiontoggle)", "if (conditionon) { #_SetActive(); } else if (conditionoff) { #_SetInactive(); } else if (conditiontoggle) { #_Toggle(); }")

			self.__outputsymbol(complete_name, "#_Pulse()", "{ #_SetActive(); #_SetInactive(); }")
			self.__outputsymbol(complete_name, "#_PulseNop()", "{ #_SetActive(); nop(); #_SetInactive(); }")

		a = [ "==", "!=" ]
		if activelow: a.reverse()
		self.__outputsymbol(complete_name, "#_IsInactive()", "(#_Get() %s 0)" % (a[0]))
		self.__outputsymbol(complete_name, "#_IsActive()", "(#_Get() %s 0)" % (a[1]))


		if (pintype == HALGenerator.PINTYPE_IN) or (pininitstate == HALGenerator.PINTYPE_IN):
			init = "{ "
			if pininitpullup == HALGenerator.VAL_ACTIVE:
				init += "#_SetPullupActive(); "
			elif pininitpullup == HALGenerator.VAL_INACTIVE:
				init += "#_SetPullupInactive(); "
			init += "#_ModeInput(); "
			init += "}"
			self.__outputsymbol(complete_name, "#_Init()", init)

		if (pintype == HALGenerator.PINTYPE_OUT) or (pininitstate == HALGenerator.PINTYPE_OUT):
			init = "{ "
			if pininitvalue == HALGenerator.VAL_LOW:
				init += "#_SetLOW(); "
			elif pininitvalue == HALGenerator.VAL_HIGH:
				init += "#_SetHIGH(); "
			elif pininitvalue == HALGenerator.VAL_ACTIVE:
				init += "#_SetActive(); "
			elif pininitvalue == HALGenerator.VAL_INACTIVE:
				init += "#_SetInactive(); "
			init += "#_ModeOutput(); "
			init += "}"
			self.__outputsymbol(complete_name, "#_Init()", init)

		self.__initializers.append(complete_name + "_Init();")

		self.__outputline()

	def __gen_portpin(self, portpin, name, descriptions):
		ppuuid = str(uuid.uuid4())
		for description in descriptions:
			self.__gen_single_portpin(portpin, name, description, ppuuid)

	def generate(self, filename, traits):
		self.__traits = traits
		self.__f = open(filename, "w")

		self.__outputline("/* Automatically generated HAL from %s */" % (self.__options["halfile"]))
		self.__outputline("/* NEVER EDIT MANUALLY */")
		self.__outputline()
		self.__outputline("/* Generated on: %s */" % (time.strftime("%Y-%m-%d %H:%M:%S")))
		self.__outputline()

		self.__outputline("#ifndef __HAL_H__")
		self.__outputline("#define __HAL_H__")
		self.__outputline()

		if self.__traits.arch in [ Traits.TRAIT_ARCH_AVR, Traits.TRAIT_ARCH_XMEGA ]:
			self.__outputline("#include <avr/io.h>")
			self.__outputline()
			self.__outputsymbol(None, "nop()", "__asm__ __volatile__(\"nop\")")
		elif self.__traits.arch == Traits.TRAIT_ARCH_I686:
			self.__outputline("extern unsigned char *addressSpace;")
			mocksymbols = [ "PORTA", "PINA", "DDRA",
							"PORTB", "PINB", "DDRB",
							"PORTC", "PINC", "DDRC",
							"PORTD", "PIND", "DDRD",
							"PORTE", "PINE", "DDRE",
							"PORTF", "PINF", "DDRF",
							"PORTG", "PING", "DDRG",
							]
			for offset in range(len(mocksymbols)):
				self.__outputsymbol(None, mocksymbols[offset], "addressSpace[%d]" % (offset))
			self.__outputsymbol(None, "nop()", "")

		self.__outputline()

		for portpin in self.__xml.portpin:
			name = portpin["name"]
			descriptions = set()
			for description in portpin.description:
				descriptions.add(description["value"])
			self.__gen_portpin(portpin, name, descriptions)

		hasport = True
		try:
			self.__xml.port
		except XMLException:
			hasport = False

		if hasport:
			for port in iter(self.__xml.HAL.port):
				name = port["name"]
				portid = name[4]
				description = port.description["value"]
				for portpinno in range(8):
					pinname = "P%s%d" % (portid, portpinno)
					pindescription = "%s%d" % (description, portpinno)
					self.__gen_portpin(port, pinname, [ pindescription ])

		self.__outputline("#define initHAL() {\\")
		for i in self.__initializers:
			self.__outputline("		%s\\" % (i))
		self.__outputline("}")

		self.__outputline()
		self.__outputline("#endif")

		self.__f.close()
		self.__f = None

