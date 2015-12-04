$( document ).ready(function() {

    // ------------------------------------------------------------------------
    // This is the global configuration of the editor.
    // ------------------------------------------------------------------------

	var config = {
		"drag_and_drop": false,
		"enable_selection": false,
		"context_menu": false,
		"context_menu_enable_modify_functions": false,
		"context_menu_enable_parser_functions": false
	}

    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

	var max_bytes_per_row = Math.ceil($("#editor_hex_wrapper").width() / 30) - 1;
	var max_bytes_per_col = 30;
	var max_bytes_per_page = max_bytes_per_col * max_bytes_per_row;
	var bytes_loaded = 0;

	var in_selection = 0;
	var selection_prev_offset = 0;
	var selection_start = 0;
	var selection_end = 0;

	var in_selection_bitfield = 0;
	var selection_prev_offset_bitfield = 0;
	var selection_start_bitfield = 0;
	var selection_end_bitfield = 0;
	
	$("#editor_tabs").tabs();

    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    function getPrimitiveItem(pItem, type, len, name) {
        $(pItem).removeClass('parser_hex_cell_ascii');
        $(pItem).removeClass('parser_hex_cell_select');

        $(pItem).addClass('unselectable');
        $(pItem).addClass('parser_primitive_cell');
		$(pItem).addClass('ctx_menu_parse_' + type);

        var minWidth = 30 * (Math.ceil(name.length / 2) - 1);
        if (minWidth < 30 * 2) minWidth = 30 * 2;
        $(pItem).css("min-width", minWidth);
        $(pItem).css("max-width", 30 * (Math.ceil(name.length / 2) - 1));
        $(pItem).css("color", "#FFFFFF");
        $(pItem).attr("offset_start", selection_start);
        $(pItem).attr("offset_end", selection_end);
        $(pItem).attr("p_type", type);
        $(pItem).attr("p_length", len);
        $(pItem).attr("p_name", name);
        name = name.toUpperCase().replace(" ", "_");
        $(pItem).text(name);
        return pItem;
    }
	
    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    function selectionBinary(type, name, fuzzable) {
        var hexview = document.getElementById('editor_hex_wrapper');
        cNodes = hexview.childNodes;
        var data = [];

        len = selection_end - selection_start;

		var bytes = JSON.parse(window.localStorage.getItem('editor_source_content'));
        for (var cc = 0; cc <= len; cc++) {
            if (cc == len) {
                data.push(bytes[selection_start + cc]);
                getPrimitiveItem($(cNodes[selection_start]), type, len + 1, name);
				console.log(JSON.stringify(data));
                $(cNodes[selection_start]).attr('p_data', JSON.stringify(data));
				$(cNodes[selection_start]).attr('p_fuzzable', fuzzable);
                break;
            }
            data.push(bytes[selection_start + cc]);
            $(cNodes[selection_start]).remove();
        }
    }

    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    function selectionStatic(type, name) {
        var hexview = document.getElementById('editor_hex_wrapper');
        cNodes = hexview.childNodes;
        var data = [];

        len = selection_end - selection_start;

		var bytes = JSON.parse(window.localStorage.getItem('editor_source_content'));
        for (var cc = 0; cc <= len; cc++) {
            if (cc == len) {
                data.push(bytes[selection_start + cc]);
                getPrimitiveItem($(cNodes[selection_start]), type, len + 1, name);
                $(cNodes[selection_start]).attr('p_data', JSON.stringify(data));
                break;
            }
            data.push(bytes[selection_start + cc]);
            $(cNodes[selection_start]).remove();
        }
    }

	
    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    function selectionString(type, name, fuzzable,
                             compression, encoder, size, padding) {

        var hexview = document.getElementById('editor_hex_wrapper');
        cNodes = hexview.childNodes;
        var data = [];

        len = selection_end - selection_start;

		var bytes = JSON.parse(window.localStorage.getItem('editor_source_content'));
        for (var cc = 0; cc <= len; cc++) {
            if (cc == len) {
                data.push(bytes[selection_start + cc]);
                getPrimitiveItem($(cNodes[selection_start]), type, len + 1, name);
                $(cNodes[selection_start]).attr('p_fuzzable', fuzzable);
                $(cNodes[selection_start]).attr('p_compression', compression);
                $(cNodes[selection_start]).attr('p_encoder', encoder);
                $(cNodes[selection_start]).attr('p_size', size);
                $(cNodes[selection_start]).attr('p_padding', padding);
                $(cNodes[selection_start]).attr('p_data', JSON.stringify(data));
                break;
            }
            data.push(bytes[selection_start + cc]);
            $(cNodes[selection_start]).remove();
        }
    }

    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    function selectionDelimiter(type, name, fuzzable) {
        var hexview = document.getElementById('editor_hex_wrapper');
        cNodes = hexview.childNodes;
        var data = [];

        len = selection_end - selection_start;

		var bytes = JSON.parse(window.localStorage.getItem('editor_source_content'));
        for (var cc = 0; cc <= len; cc++) {
            if (cc == len) {
                data.push(bytes[selection_start + cc]);
                getPrimitiveItem($(cNodes[selection_start]), type, len + 1, name);
                $(cNodes[selection_start]).attr('p_fuzzable', fuzzable);
                $(cNodes[selection_start]).attr('p_data', JSON.stringify(data));
                break;
            }
            data.push(bytes[selection_start + cc]);
            $(cNodes[selection_start]).remove();
        }
    }
	
    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    function selectionNumeric(type, name, fuzzable,
                              endian, signed, format, full_range) {
        var hexview = document.getElementById('editor_hex_wrapper');
        cNodes = hexview.childNodes;
        var data = [];

		len = selection_end - selection_start;

        switch(len + 1) {
            case 1:
                type = "byte";
                break;
            case 2:
                type = "word";
                break;
            case 4:
                type = "dword";
                break;
            case 8:
                type = "qword";
                break;
            default:
                alert("Not a byte, word, dword or qword.");
                return;
        }

		var bytes = JSON.parse(window.localStorage.getItem('editor_source_content'));
        for (var cc = 0; cc <= len; cc++) {
            if (cc == len) {
                data.push(bytes[selection_start + cc]);
                getPrimitiveItem($(cNodes[selection_start]), type, len + 1, name);
                $(cNodes[selection_start]).attr('p_fuzzable', fuzzable);
                $(cNodes[selection_start]).attr('p_data', JSON.stringify(data));
                $(cNodes[selection_start]).attr('p_endian', endian);
                $(cNodes[selection_start]).attr('p_signed', signed);
                $(cNodes[selection_start]).attr('p_format', format);
                $(cNodes[selection_start]).attr('p_full_range', full_range);
                break;
            }
            data.push(bytes[selection_start + cc]);
            $(cNodes[selection_start]).remove();
        }
    }

    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

	function dec2bin(dec){
		return (dec >>> 0).toString(2);
	}
	
    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    function setSelection(type, area) {
        var length = area.end - area.start + 1;

        switch(type) {
            case "block":
                $("#dialog_block").dialog({
                    "title": "Block Properties",
                    "closeText": "Cancel",
                    buttons: [ { id:"b_parse_block",
                                 text: "Save",
                                 click: function() {
                                     var name = $("#parser_p_block_name").val();
                                     var group = $("#parser_p_block_group").val();
                                     var encoder = $("#parser_p_block_encoder").val();
                                     var dep_on = $("#parser_p_block_dep_on").val();
                                     var dep_values = $("#parser_p_block_dep_values").val();
                                     var dep_compare = $("#parser_p_block_dep_compare").val();
                                     createBlock(name, area, group, encoder,
                                                 dep_on, dep_values,
                                                 dep_compare);
                                     $( this ).dialog( "close" ); }
                               } ]
                });
                break;
            case "numeric":
                $("#dialog_numeric").dialog({
                    "title": "Numeric Primitive",
                    "closeText": "Cancel",
                    buttons: [ { id:"b_parse_numeric",
                                 text: "Save",
                                 click: function() {
                                     var name = $("#parser_p_numeric_name").val();
                                     var fuzzable = $("#p_numeric_fuzzable").val();
                                     var endian = $("#p_numeric_endian").val();
                                     var signed = $("#p_numeric_signed").val();
                                     var format = $("#p_numeric_format").val();
                                     var full_range = $("#p_numeric_full_range").val();

                                     selectionNumeric(type, name,
                                                      fuzzable, endian, signed, format,
                                                      full_range);
                                     $( this ).dialog( "close" ); }
                               } ]
                });
                break;
            case "bitfield":
				$("#bitfield_bits_container").html('');
				var bytes = JSON.parse(window.localStorage.getItem('editor_source_content'));				
				var hexview = document.getElementById('editor_hex_wrapper');
				cNodes = hexview.childNodes;
		
				var num_bytes = (selection_end - selection_start) + 1;

				if (num_bytes > 8) {
					alert("Bitfields longer than 8 bytes are not supported.");
					return;
				}
				
				bitcounter = 0;
				for (var bc = selection_start; bc <= selection_end; bc++) {
					var byte_offset = $(cNodes[bc]).attr('offset');
					var bin_string = dec2bin(bytes[byte_offset].dec);
					var n_padding = 8 - bin_string.length;
					var bin = "";
					for (var x = 0; x < n_padding; x++) bin += "0";
					bin += bin_string;

					for (var x = 0; x < bin.length; x++) {
						var div = '<div position=' + bitcounter + ' class="unselectable bitfield_item';
						if ((x + 1) % 8 == 0) {
							div += ' bitfield_mright';
						}
						$("#bitfield_bits_container").append(div + '">' + bin[x] + '</div>');
						bitcounter++;
					}
				}
			
                $("#dialog_bitfield").dialog({
                    "title": "Bitfield Primitive",
                    "closeText": "Cancel",
                    buttons: [ { id:"b_parse_bitfield",
                                 text: "Save",
                                 click: function() {
                                     var name = $("#parser_p_bitfield_name").val();
                                     var fuzzable = $("#p_bitfield_fuzzable").val();
									 var length = "";	// number of bytes selected
									 var value = "";	// the hex value of complete selection
									 
									 // selectionBitfield("bitfield", name, value, length, fuzzable);

                                     $( this ).dialog( "close" ); }
                               } ]
                });
                break;
            case "string":
                $("#dialog_string").dialog({
                    "title": "String Primitive",
                    "closeText": "Cancel",
                    buttons: [ { id:"b_parse_string",
                                 text: "Save",
                                 click: function() {
                                     var name = $("#parser_p_string_name").val();
                                     var fuzzable = $("#p_string_fuzzable").val();
                                     var compression = $("#p_string_compression").val();
                                     var encoder = $("#p_string_encoder").val();
                                     var size = $("#p_string_size").val();
                                     var padding = $("#p_string_padding_byte").val();
                                     selectionString(type, name,
                                                     fuzzable, compression, encoder,
                                                     size, padding);
                                     $( this ).dialog( "close" ); }
                               } ]
                });
                break;
            case "binary":
                $("#dialog_binary").dialog({
                    "title": "Binary Primitive",
                    "closeText": "Cancel",
                    buttons: [ { id:"b_parse_binary",
                                 text: "Save",
                                 click: function() {
                                     var name = $("#parser_p_binary_name").val();
									 var fuzzable = $("#p_binary_fuzzable").val();
                                     selectionBinary(type, name, fuzzable);
                                     $( this ).dialog( "close" ); }
                               } ]
                });
                break;
            case "static":
                $("#dialog_static").dialog({
                    "title": "Static Primitive",
                    "closeText": "Cancel",
                    buttons: [ { id:"b_parse_static",
                                 text: "Save",
                                 click: function() {
                                     var name = $("#parser_p_static_name").val();
                                     selectionBinary(type, name);
                                     $( this ).dialog( "close" ); }
                               } ]
                });
                break;
            case "delimiter":
                $("#dialog_delimiter").dialog({
                    "title": "Delimiter Primitive",
                    "closeText": "Cancel",
                    buttons: [ { id:"b_parse_delimiter",
                                 text: "Save",
                                 click: function() {
                                     var name = $("#parser_p_delimiter_name").val();
                                     var fuzzable = $("#p_delimiter_fuzzable").val();
                                     selectionDelimiter(type, name, fuzzable);
                                     $( this ).dialog( "close" ); }
                               } ]
                });
                break;
        }
    }
	
    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------
	
	function parse_selection(item, p_type) {
		if ((selection_end < selection_start) || (selection_end == 0 && selection_start == 0)) {
			alert("Selection required.");
			return;
		}
        var color = $(item).css('background-color');
        setSelection(p_type, {"start": selection_start, "end": selection_end});
	}

    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------
	
	function breakPrimitive(item) {
        if ($(item).hasClass('parser_primitive_cell') == false) {
            alert("Error: Not a primitive.");
            return;
        }
		var hexview = document.getElementById('editor_hex_wrapper');
		var file_data = JSON.parse(window.localStorage.getItem('editor_source_content'));

        var p_data = JSON.parse($(item).attr('p_data'));
        var p_offset_start = $(item).attr('offset_start');

        for (var cnc = 0; cnc < p_data.length; cnc++) {
            var hvItem = hexViewByte(p_data[cnc]);
            $(item).before(hvItem);
        }
        $(item).remove();
	}
	
    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

	if (config.context_menu) {
		$('#the-node').contextMenu({
			selector: 'div.editor_hex_cell', 
			callback: function(key, options) {
				if (key == "s_ascii") toAscii($(this));
				if (key == "s_hex") toHex($(this));
				if (key == "s_modify") changeValue($(this));
				if (key == "s_delete") deleteValue($(this));
				if (key == "s_break") breakPrimitive($(this));
				if (key == "parse_binary") parse_selection($(this), "binary");
				if (key == "parse_bitfield") parse_selection($(this), "bitfield");
				if (key == "parse_numeric") parse_selection($(this), "numeric");
				if (key == "parse_delimiter") parse_selection($(this), "delimiter");
				if (key == "parse_static") parse_selection($(this), "static");
				if (key == "parse_string") parse_selection($(this), "string");
				if (key == "parse_size") parse_selection($(this), "size");
				if (key == "parse_checksum") parse_selection($(this), "checksum");
				if (key == "parse_block") parse_selection($(this), "block");
				if (key == "parse_repeater") parse_selection($(this), "repeater");
				if (key == "parse_padding") parse_selection($(this), "padding");
			},
			items: function() {	
			
				menu = {}

				menu.view  = {
					name: "View",
					items: function() { 
						s_menu_0 = {};
							s_menu_0.s_hex    = {name: "To Hex", class_name: "ctx_menu_item"};
							s_menu_0.s_ascii  = {name: "To Ascii", class_name: "ctx_menu_item"};
						return(s_menu_0);
					}
				}
				
				if (config.context_menu_enable_modify_functions) {
					menu.edit  = {
						name: "Edit",
					    items: function() { 
							s_menu_1 = {};
								s_menu_1.s_modify    = {name: "Modify", class_name: "ctx_menu_item"};
								s_menu_1.s_delete    = {name: "Delete", class_name: "ctx_menu_item"};
								s_menu_1.s_break     = {name: "Break Primitive", class_name: "ctx_menu_item"};
							return(s_menu_1);
						}
					}
				}
		
				if (config.context_menu_enable_parser_functions) {
					menu.parse  = {
						name: "Parse",
					    items: function() { 
							s_menu_2 = {};
								s_menu_2.hdr_primitive   = {name: "Primitive",    class_name: "ctx_menu_header_primitive"};
								s_menu_2.parse_binary    = {name: "Binary",       class_name: "ctx_menu_parse_binary"};
								s_menu_2.parse_bitfield  = {name: "Bitfield",     class_name: "ctx_menu_parse_bitfield"};
								s_menu_2.parse_numeric   = {name: "Numeric",      class_name: "ctx_menu_parse_numeric"};
								s_menu_2.parse_delimiter = {name: "Delimiter",    class_name: "ctx_menu_parse_delimiter"};
								s_menu_2.parse_static    = {name: "Static",       class_name: "ctx_menu_parse_static"};
								s_menu_2.parse_string    = {name: "String",       class_name: "ctx_menu_parse_string"};
								s_menu_2.hdr_block       = {name: "Block",        class_name: "ctx_menu_header_block"};
								s_menu_2.parse_block     = {name: "Block",        class_name: "ctx_menu_parse_block"};
								s_menu_2.parse_checksum  = {name: "Checksum",     class_name: "ctx_menu_parse_checksum"};
								s_menu_2.parse_size      = {name: "Size",         class_name: "ctx_menu_parse_size"};
								s_menu_2.parse_repeater  = {name: "Repeat Block", class_name: "ctx_menu_parse_repeat_block"};
								s_menu_2.parse_padding   = {name: "Padding",      class_name: "ctx_menu_parse_pad_block"};
							return(s_menu_2);
						}
					}
				}
			
				return(menu);
			}
		});
	}

    // ------------------------------------------------------------------------
	// Check if the target is a byte or a sequence of bytes from the hex editor.
	//
    // 'item' is the actual item the mouse was pointing at when the user 
	// clicked the button. We have to check whether the item is a member of a
	// selection to determine whether to work on a single byte or a sequence
	// of bytes.
    // ------------------------------------------------------------------------
	
	function getStartEndOffset(item) {
		var o_start = -1;
		var o_end = -1;
		
		if ($(item).hasClass("editor_hex_cell_select") == true) {
			o_start = selection_start;
			o_end = selection_end;
		} else {
			o_start = $(item).attr('offset');
			o_end = $(item).attr('offset');
		}
		return ({"start": o_start,"end": o_end});
	}

    // ------------------------------------------------------------------------
	// Delete a byte or a sequence of bytes from the hex editor, based on
	// selection.
    // ------------------------------------------------------------------------
	
	function deleteValue(item) {
		var o_start = getStartEndOffset(item).start;
		var o_end = getStartEndOffset(item).end;
		
		var bytes = JSON.parse(window.localStorage.getItem('editor_source_content'));
		var hexView = document.getElementById('editor_hex_wrapper');
        var cNodes = hexView.childNodes;
		
        for (var cnc = o_end; cnc >= o_start; cnc--) {
			$(cNodes[cnc]).remove();
			bytes.splice(cnc, 1);
        }
									
		// Here we have to update all the remaining elements with the
		// new offsets.
		// This implementation is ugly as hell but not being a JS guy I
		// could not yet find a way to wait with saving bytes back to 
		// localStorage until the for loop finished.

		for (var cnc = 0; cnc <= bytes.length; cnc++) {
			try {
				$(cNodes[cnc]).attr('offset', cnc);
			} catch(error) {}
			bytes[cnc].offset = cnc;
			if (cnc >= bytes.length - 1) {
				window.localStorage.setItem('editor_source_content', 
											JSON.stringify(bytes));
				processPythonView();
				processCView();
			}
        }

		// Refresh
		$(hexView).hide().show(0);
	}
	
    // ------------------------------------------------------------------------
    // Display a byte or a sequence of bytes as ASCII in the hex editor, based
	// on selection.
    // ------------------------------------------------------------------------

    function toAscii(item) {
		var o_start = getStartEndOffset(item).start;
		var o_end = getStartEndOffset(item).end;
		
		var bytes = JSON.parse(window.localStorage.getItem('editor_source_content'));
		var hexView = document.getElementById('editor_hex_wrapper');
        var cNodes = hexView.childNodes;
        for (var cnc = o_start; cnc <= o_end; cnc++) {
			if (bytes[cnc].dec > 126 || bytes[cnc].dec < 32) continue;
            $(cNodes[cnc]).text(bytes[cnc].raw);
        }
    }

    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    function toHex(item) {
		var o_start = -1;
		var o_end = -1;
		
		if ($(item).hasClass("editor_hex_cell_select") == true) {
			o_start = selection_start;
			o_end = selection_end;
		} else {
			o_start = $(item).attr('offset');
			o_end = $(item).attr('offset');
		}

		var bytes = JSON.parse(window.localStorage.getItem('editor_source_content'));
		var hexView = document.getElementById('editor_hex_wrapper');
        var cNodes = hexView.childNodes;
        for (var cnc = o_start; cnc <= o_end; cnc++) {
            $(cNodes[cnc]).text(bytes[cnc].hex);
        }
    }
	
    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    $("body").on('mouseup', 'div.parser_hex_cell', function(evt) {
		if (config.enable_selection == false) return;
		in_selection = 0;
        selection_end = parseInt($(evt.target).attr('offset'));
    });
	
	// ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    $("body").on('mousedown', 'div.editor_hex_cell', function(evt) {
		if (config.enable_selection == false) return;
        /*
            1 = Left   mouse button
            2 = Centre mouse button
            3 = Right  mouse button
        */
        if (in_selection == 0 && evt.which === 1) {
			clearAllSelection('hexeditor');
			selection_start = Array.prototype.indexOf.call(evt.target.parentNode.childNodes, evt.target);
			selectByte(evt.target);
			in_selection = 1;
		} else if (in_selection == 1 && evt.which === 1) {
			selection_end = Array.prototype.indexOf.call(evt.target.parentNode.childNodes, evt.target);
			in_selection = 0;
		}
    });

    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    function selectByte(item) {
		if (config.enable_selection == false) return;
		$(item).addClass("editor_hex_cell_select");
    }

    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    function selectBytes(end_offset) {
		if (config.enable_selection == false) return;
		if (selection_prev_offset > end_offset) {
		    clearSelection('hexeditor', end_offset, selection_prev_offset);
		}		
		var hexView = document.getElementById('editor_hex_wrapper');
        var cNodes = hexView.childNodes;
        for (var cnc = selection_start; cnc <= end_offset; cnc++) {
			selectByte(cNodes[cnc]);
        }
    }
	
    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    $("body").on('mouseover', 'div.editor_hex_cell', function(evt) {
        $(evt.target).addClass("editor_hex_cell_mark");
        var offset_info = $("div#offset_info").get(0);
        var byte_info_hex = $("div#byte_info_hex").get(0);
        var byte_info_dec = $("div#byte_info_dec").get(0);
        var byte_info_raw = $("div#byte_info_raw").get(0);

		var offset = evt.target.getAttribute('offset');
		var visible_offset = Array.prototype.indexOf.call(evt.target.parentNode.childNodes, evt.target);
		var byte_val = JSON.parse(window.localStorage.getItem('editor_source_content'))[offset];
	
        var offset_info = document.getElementById('offset_info');
        byte_info_raw.textContent = "Raw: " + byte_val.raw;
        byte_info_dec.textContent = "Dec: " + byte_val.dec;
        byte_info_hex.textContent = "Hex: " + byte_val.hex;
        offset_info.textContent = "Offset: " + byte_val.offset;
		
		if (in_selection) selectBytes(visible_offset);

		selection_prev_offset = visible_offset;
    });

    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    $("body").on('mouseout', 'div.editor_hex_cell', function(evt) {
        $(evt.target).removeClass("editor_hex_cell_mark");
    });

    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------
	
	$("#editor_hex_wrapper").scroll(function() {
	    var item = $("#editor_hex_wrapper").get(0);
		var current = $(this).scrollTop();
		var scroll_percent = ($(this).scrollTop() / (item.scrollHeight - item.clientHeight)) * 100;
	    if (scroll_percent == 100) {
			processHexView();
			$(item).hide().show(0);
			$(this).scrollTop($(this).scrollTop() - 0.1);
		}
	});
	
    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    function formatHex(val) {
        if (val.length % 2) return ("0" + val);
        return val;
    }

    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    function hexViewByte(byte_val) {
        var item = document.createElement('div');
        item.setAttribute('class', 'unselectable editor_hex_cell');
        item.setAttribute('offset', byte_val.offset);
        item.textContent = byte_val.hex;
        return item;
    }
	
    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

	function updateLoadingStatus(current = 0) {
		var maximum = $(".editor-load-progress-bar").attr('aria-valuemax');
		$(".editor-load-progress-bar").attr('aria-valuenow', current);
		$(".editor-load-progress-bar").css('width', ((current / maximum) * 100) +'%').attr('aria-valuenow', current);
	}
	
    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    function processHexView() {
        var hexview = document.getElementById('editor_hex_wrapper');
        var file_data = JSON.parse(window.localStorage.getItem('editor_source_content'));
		var loaded = bytes_loaded;
		
        for (bcnt = loaded; bcnt < loaded + max_bytes_per_page; bcnt++) {
			updateLoadingStatus(bytes_loaded);
			if (bytes_loaded >= file_data.length) {
				break;
			}
            var hvItem = hexViewByte(file_data[bcnt]);
            hexview.appendChild(hvItem);
			bytes_loaded += 1;
        }
    }
	
    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    function processPythonView() {
		var pythonview = document.getElementById('editor_python_wrapper');
        var file_data = JSON.parse(window.localStorage.getItem('editor_source_content'));
        pythonview.innerHTML = "";
        var bcnt = 0;

		var python_code = "payload = [";
		
        for (bcnt = 0; bcnt < file_data.length; bcnt++) {
			if (bcnt % 8) {
				python_code += ", ";
			} else {
				python_code += "<br>&nbsp;&nbsp;&nbsp;&nbsp;";
			}
			python_code += "0x" + file_data[bcnt].hex;
        }
		
		python_code += "<br>]<br>payload = ''.join(payload)<br>";
		pythonview.innerHTML = python_code;
    }
	
    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    function processCView() {
		var cview = document.getElementById('editor_c_wrapper');
        var file_data = JSON.parse(window.localStorage.getItem('editor_source_content'));
        cview.innerHTML = "";
        var bcnt = 0;

		var c_code = "char payload[] = \"";
		
        for (bcnt = 0; bcnt < file_data.length; bcnt++) {
			if (!(bcnt % 16)) {
			    c_code += "\"<br>&nbsp;&nbsp;&nbsp;&nbsp;\"";
			}
			c_code += "\\x" + file_data[bcnt].hex;
        }
		
		c_code += "\";<br>";
		cview.innerHTML = c_code;
    }

    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------
	
	function displayData() {
		processHexView();
		processPythonView();
		processCView();
	}
	
    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    $("body").on('mouseout', 'div.bitfield_item', function(evt) {
        $(evt.target).removeClass("bitfield_item_cell_mark");
    });

    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    function selectBit(item) {
		if (config.enable_selection == false) return;
		$(item).addClass("editor_bitfield_selected");
    }

    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    function selectBits(end_offset) {
		if (config.enable_selection == false) return;
		if (selection_prev_offset_bitfield > end_offset) {
		    clearSelection('bitfield', end_offset, selection_prev_offset_bitfield);
		}		
		var hexView = document.getElementById('bitfield_bits_container');
        var cNodes = hexView.childNodes;
        for (var cnc = selection_start_bitfield; cnc <= end_offset; cnc++) {
			selectBit(cNodes[cnc]);
        }
    }

    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    function clearSelection(type, start, end) {
		if (config.enable_selection == false) return;
		var id = '';
		var r_class = '';
		switch(type) {
			case 'hexeditor':
				id = 'editor_hex_wrapper';
				r_class = 'editor_hex_cell_select';
				break;
			case 'bitfield':
				id = 'bitfield_bits_container';
				r_class = 'editor_bitfield_selected';
				break;
			default:
				return;
		}
		var view = document.getElementById(id);
        var cNodes = view.childNodes;
        for (var cnc = start; cnc <= end; cnc++) {
            $(cNodes[cnc]).removeClass(r_class);
        }
    }

    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    function clearAllSelection(type) {
		var id = '';
		var r_class = '';
		switch(type) {
			case 'hexeditor':
				id = 'editor_hex_wrapper';
				r_class = 'editor_hex_cell_select';
				break;
			case 'bitfield':
				id = 'bitfield_bits_container';
				r_class = 'editor_bitfield_selected';
				break;
			default:
				return;
		}
		if (config.enable_selection == false) return;
		var view = document.getElementById(id);
        var cNodes = view.childNodes;
        for (var cnc = 0; cnc < cNodes.length; cnc++) {
            $(cNodes[cnc]).removeClass(r_class);
        }
    }

	// ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    $("body").on('mousedown', 'div.bitfield_item', function(evt) {
		if (config.enable_selection == false) return;
		if (evt.which !== 1) return;
        if (in_selection_bitfield == 0) {
			clearAllSelection('bitfield');
			selection_start_bitfield = Array.prototype.indexOf.call(evt.target.parentNode.childNodes, evt.target);
			selectBit(evt.target);
			in_selection_bitfield = 1;
		} else {
			selection_end_bitfield = Array.prototype.indexOf.call(evt.target.parentNode.childNodes, evt.target);
			in_selection_bitfield = 0;
		}
    });

    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    $("body").on('mouseup', 'div.bitfield_item', function(evt) {
		if (config.enable_selection == false) return;
		selection_end_bitfield = parseInt($(evt.target).attr('position'));
    });
	
    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------

    $("body").on('mouseover', 'div.bitfield_item', function(evt) {
		var visible_offset = Array.prototype.indexOf.call(evt.target.parentNode.childNodes, evt.target);
		if (in_selection_bitfield == 1) {
			$(evt.target).addClass("editor_bitfield_selected");
			selectBits(visible_offset);
			selection_prev_offset_bitfield = visible_offset;
		} else {
			$(evt.target).addClass("bitfield_item_cell_mark");
		}
    });

    // ------------------------------------------------------------------------
    //
    // ------------------------------------------------------------------------
        
    function processData(format, data, callback) {
        try {
            if (format == "base64") data = window.atob(data);
        } catch(error) {
            alert("Error: data is not valid Base64, treating it as raw binary.");
            console.log(error);
        }
        var processed_data = [];
                
        for (var bcnt = 0; bcnt < data.length; bcnt++) {
            processed_data.push({ 
                    "raw": data[bcnt],
                    "dec": data[bcnt].charCodeAt(0),
                    "hex": formatHex(data[bcnt].charCodeAt(0).toString(16)).toUpperCase(),
                    "offset": bcnt
            });
        }
        window.localStorage.setItem('editor_source_content', 
                                    JSON.stringify(processed_data));
        $(".editor-load-progress-bar").attr('aria-valuemax', processed_data.length);
        callback();
    }

    // ------------------------------------------------------------------------
    // TODO: THERE MUST BE A BETTER WAY TO DO THIS...
    // ------------------------------------------------------------------------

    var prev = "";
    var interval = "";

    function update() {
        var payload_data = $("#payload_holder").attr('payload');
        if (payload_data != prev) {
            $('#editor_hex_wrapper').get(0).innerHTML = '';
            $('#editor_hex_wrapper').hide().show(0);
            bytes_loaded = 0;
            processData("base64", payload_data, displayData);
            prev = payload_data;
            clearInterval(interval);
        }
    }

    interval = setInterval(update, 1000);

});

