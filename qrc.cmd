# process_technology
	# -technology_library_file "qrc_tech.lib"
	# -technology_name "LALA"

 output_setup \
	-net_name_space layout \
	-directory_name ./name

 extraction_setup \
	-max_fracture_length 50 \
	-test 1

 input_db \
	-type calibre \
	-directory_name ./calibre \
	-run_name Design \
	-layer_map_file ./layer.map \
	-device_property_value 7 \
	-instance_property_value 6 \
	-net_property_value 5

output_db \
	-type spef \
	-subtype standard

 extract \
	-selection all \
	-type rc_decoupled

graybox \
	-type none

# log_file
	# -type out
	# -file_name qrc.log
	# -dump_options true

# log_file2
	# -type none
	# -file_name qrc.log
	# -dump_options true

filter_coupling_cap \
	-coupling_cap_threshold_relative 0.05
