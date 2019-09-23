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

class Traits():
	TRAIT_ARCH_I686 = 0
	TRAIT_ARCH_AVR = 1
	TRAIT_ARCH_XMEGA = 2

	def __init__(self, trait):
		if trait == Traits.TRAIT_ARCH_I686:
			self.arch = Traits.TRAIT_ARCH_I686
		elif trait == Traits.TRAIT_ARCH_AVR:
			self.arch = Traits.TRAIT_ARCH_AVR
		elif trait == Traits.TRAIT_ARCH_XMEGA:
			self.arch = Traits.TRAIT_ARCH_XMEGA
		else:
			raise Exception("Unknown trait.")
