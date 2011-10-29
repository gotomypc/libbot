import gtk
import pango

import bot_procman.sheriff as sheriff
import bot_procman.sheriff_gtk.command_model as cm
import bot_procman.sheriff_gtk.sheriff_dialogs as sd

class SheriffCommandTreeView(gtk.TreeView):
    def __init__(self, _sheriff, cmds_ts, gui_config):
        super(SheriffCommandTreeView, self).__init__(cmds_ts)
        self.cmds_ts = cmds_ts
        self.sheriff = _sheriff

        cmds_tr = gtk.CellRendererText ()
        cmds_tr.set_property ("ellipsize", pango.ELLIPSIZE_END)
        plain_tr = gtk.CellRendererText ()
        status_tr = gtk.CellRendererText ()

        cols_to_make = [ \
            ("Name",     cmds_tr,   cm.COL_CMDS_TV_CMD,  None),
            ("Host",     plain_tr,  cm.COL_CMDS_TV_HOST, None),
            ("Status",   status_tr, cm.COL_CMDS_TV_STATUS_ACTUAL, self._status_cell_data_func),
            ("CPU %",    plain_tr,  cm.COL_CMDS_TV_CPU_USAGE, None),
            ("Mem (kB)", plain_tr,  cm.COL_CMDS_TV_MEM_VSIZE, None),
            ]

        self.columns = []
        for name, renderer, col_id, cell_data_func in cols_to_make:
            col = gtk.TreeViewColumn(name, renderer, text=col_id)
            col.set_sort_column_id(col_id)
            col.set_visible(gui_config.show_columns[col_id])
            if cell_data_func:
                col.set_cell_data_func(renderer, cell_data_func)
            self.columns.append(col)

        # set an initial width for the name column
        self.columns[0].set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        self.columns[0].set_fixed_width(150)

        for col in self.columns:
            col.set_resizable (True)
            self.append_column (col)

        cmds_sel = self.get_selection ()
        cmds_sel.set_mode (gtk.SELECTION_MULTIPLE)

        self.add_events (gtk.gdk.KEY_PRESS_MASK | \
                gtk.gdk.BUTTON_PRESS | gtk.gdk._2BUTTON_PRESS)
        self.connect ("key-press-event", 
                self._on_cmds_tv_key_press_event)
        self.connect ("button-press-event", 
                self._on_cmds_tv_button_press_event)
        self.connect ("row-activated",
                self._on_cmds_tv_row_activated)

        # commands treeview context menu
        self.cmd_ctxt_menu = gtk.Menu ()

        self.start_cmd_ctxt_mi = gtk.MenuItem ("_Start")
        self.cmd_ctxt_menu.append (self.start_cmd_ctxt_mi)
        self.start_cmd_ctxt_mi.connect ("activate", 
                self._start_selected_commands)

        self.stop_cmd_ctxt_mi = gtk.MenuItem ("_Stop")
        self.cmd_ctxt_menu.append (self.stop_cmd_ctxt_mi)
        self.stop_cmd_ctxt_mi.connect ("activate", self._stop_selected_commands)

        self.restart_cmd_ctxt_mi = gtk.MenuItem ("R_estart")
        self.cmd_ctxt_menu.append (self.restart_cmd_ctxt_mi)
        self.restart_cmd_ctxt_mi.connect ("activate", 
                self._restart_selected_commands)

        self.remove_cmd_ctxt_mi = gtk.MenuItem ("_Remove")
        self.cmd_ctxt_menu.append (self.remove_cmd_ctxt_mi)
        self.remove_cmd_ctxt_mi.connect ("activate", 
                self._remove_selected_commands)

        self.change_deputy_ctxt_mi = gtk.MenuItem ("_Change Host")
        self.cmd_ctxt_menu.append (self.change_deputy_ctxt_mi)
        self.change_deputy_ctxt_mi.show ()

        self.cmd_ctxt_menu.append (gtk.SeparatorMenuItem ())

        self.new_cmd_ctxt_mi = gtk.MenuItem ("_New Command")
        self.cmd_ctxt_menu.append (self.new_cmd_ctxt_mi)
        self.new_cmd_ctxt_mi.connect ("activate", 
                lambda *s: sd.do_add_command_dialog(self.sheriff, self.cmds_ts, self.get_toplevel()))

        self.cmd_ctxt_menu.show_all ()

#        # drag and drop command rows for grouping
#        dnd_targets = [ ('PROCMAN_CMD_ROW', 
#            gtk.TARGET_SAME_APP | gtk.TARGET_SAME_WIDGET, 0) ]
#        self.enable_model_drag_source (gtk.gdk.BUTTON1_MASK, 
#                dnd_targets, gtk.gdk.ACTION_MOVE)
#        self.enable_model_drag_dest (dnd_targets, 
#                gtk.gdk.ACTION_MOVE)

    def get_columns(self):
        return self.columns

    def get_selected_commands (self):
        selection = self.get_selection ()
        if selection is None: return []
        model, rows = selection.get_selected_rows ()
        assert model is self.cmds_ts
        return self.cmds_ts.rows_to_commands(rows)

    def _start_selected_commands (self, *args):
        for cmd in self.get_selected_commands ():
            self.sheriff.start_command (cmd)

    def _stop_selected_commands (self, *args):
        for cmd in self.get_selected_commands ():
            self.sheriff.stop_command (cmd)

    def _restart_selected_commands (self, *args):
        for cmd in self.get_selected_commands ():
            self.sheriff.restart_command (cmd)

    def _remove_selected_commands (self, *args):
        for cmd in self.get_selected_commands ():
            self.sheriff.schedule_command_for_removal (cmd)

    def _on_cmds_tv_key_press_event (self, widget, event):
        if event.keyval == gtk.gdk.keyval_from_name ("Right"):
            # expand a group row when user presses right arrow key
            model, rows = self.get_selection ().get_selected_rows ()
            if len (rows) == 1:
                model_iter = model.get_iter (rows[0])
                if model.iter_has_child (model_iter):
                    self.expand_row (rows[0], True)
                return True
        elif event.keyval == gtk.gdk.keyval_from_name ("Left"):
            # collapse a group row when user presses left arrow key
            model, rows = self.get_selection ().get_selected_rows ()
            if len (rows) == 1:
                model_iter = model.get_iter (rows[0])
                if model.iter_has_child (model_iter):
                    self.collapse_row (rows[0])
                else:
                    parent = model.iter_parent (model_iter)
                    if parent:
                        parent_path = self.cmds_ts.get_path (parent)
                        self.set_cursor (parent_path)
                return True
        return False

    def _on_cmds_tv_button_press_event (self, treeview, event):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            time = event.time
            treeview.grab_focus ()
            sel = self.get_selection ()
            model, rows = sel.get_selected_rows ()
            pathinfo = treeview.get_path_at_pos (int (event.x), int (event.y))

            if pathinfo is not None:
                if pathinfo[0] not in rows:
                    # if user right-clicked on a previously unselected row,
                    # then unselect all other rows and select only the row
                    # under the mouse cursor
                    path, col, cellx, celly = pathinfo
                    treeview.grab_focus ()
                    treeview.set_cursor (path, col, 0)

                # build a submenu of all deputies
#                selected_cmds = self.get_selected_commands ()
#                can_start_stop_remove = len(selected_cmds) > 0 and \
#                        not self.sheriff.is_observer ()

                deputy_submenu = gtk.Menu ()
                deps = [ (d.name, d) for d in self.sheriff.get_deputies () ]
                deps.sort ()
                for name, deputy in deps:
                    dmi = gtk.MenuItem (name)
                    deputy_submenu.append (dmi)
                    dmi.show ()

                    def _onclick (mi, newdeputy):
                        for cmd in self.get_selected_commands ():
                            old_dep = self.sheriff.get_command_deputy (cmd)

                            if old_dep == newdeputy: continue

                            self.sheriff.move_command_to_deputy(cmd, newdeputy)

                    dmi.connect ("activate", _onclick, deputy)

                self.change_deputy_ctxt_mi.set_submenu (deputy_submenu)
            else:
                sel.unselect_all ()

            # enable/disable menu options based on sheriff state and user
            # selection
            can_add_load = not self.sheriff.is_observer () and\
                    not self.sheriff.get_active_script()
            can_modify = pathinfo is not None and \
                    not self.sheriff.is_observer() and \
                    not self.sheriff.get_active_script()

            self.start_cmd_ctxt_mi.set_sensitive (can_modify)
            self.stop_cmd_ctxt_mi.set_sensitive (can_modify)
            self.restart_cmd_ctxt_mi.set_sensitive (can_modify)
            self.remove_cmd_ctxt_mi.set_sensitive (can_modify)
            self.change_deputy_ctxt_mi.set_sensitive (can_modify)
            self.new_cmd_ctxt_mi.set_sensitive (can_add_load)

            self.cmd_ctxt_menu.popup (None, None, None, event.button, time)
            return 1
        elif event.type == gtk.gdk._2BUTTON_PRESS and event.button == 1:
            # expand or collapse groups when double clicked
            sel = self.get_selection ()
            model, rows = sel.get_selected_rows ()
            if len (rows) == 1:
                if model.iter_has_child (model.get_iter (rows[0])):
                    if self.row_expanded (rows[0]):
                        self.collapse_row (rows[0])
                    else:
                        self.expand_row (rows[0], True)
        elif event.type == gtk.gdk.BUTTON_PRESS and event.button == 1:
            # unselect all rows when the user clicks on empty space in the
            # commands treeview
            time = event.time
            x = int (event.x)
            y = int (event.y)
            pathinfo = treeview.get_path_at_pos (x, y)
            if pathinfo is None:
                self.get_selection ().unselect_all ()
                
    def _on_cmds_tv_row_activated (self, treeview, path, column):
        cmd = self.cmds_ts.path_to_command(path)
        if not cmd:
            return

        old_deputy = self.sheriff.get_command_deputy (cmd)
        dlg = sd.AddModifyCommandDialog (self.get_toplevel(), 
                self.sheriff.get_deputies (),
                self.cmds_ts.get_known_group_names (),
                cmd.name, cmd.nickname, old_deputy, 
                cmd.group, cmd.auto_respawn)
        if dlg.run () == gtk.RESPONSE_ACCEPT:
            newname = dlg.get_command ()
            newnickname = dlg.get_nickname ()
            newdeputy = dlg.get_deputy ()
            newgroup = dlg.get_group ().strip ()
            newauto_respawn = dlg.get_auto_respawn ()

            if newname != cmd.name:
                self.sheriff.set_command_name (cmd, newname)

            if newnickname != cmd.nickname:
                self.sheriff.set_command_nickname (cmd, newnickname)

            if newauto_respawn != cmd.auto_respawn:
                self.sheriff.set_auto_respawn (cmd, newauto_respawn)

            if newdeputy != old_deputy:
                self.sheriff.move_command_to_deputy(cmd, newdeputy)

            if newgroup != cmd.group:
                self.sheriff.set_command_group (cmd, newgroup)
        dlg.destroy ()

    def _status_cell_data_func (self, column, cell, model, model_iter):
        color_map = {
                sheriff.TRYING_TO_START : "Orange",
                sheriff.RESTARTING : "Orange",
                sheriff.RUNNING : "Green",
                sheriff.TRYING_TO_STOP : "Yellow",
                sheriff.REMOVING : "Yellow",
                sheriff.STOPPED_OK : "White",
                sheriff.STOPPED_ERROR : "Red",
                sheriff.UNKNOWN : "Red"
                }

        assert model is self.cmds_ts
        cmd = self.cmds_ts.iter_to_command(model_iter)
        if not cmd:
            # group node
            child_iter = model.iter_children (model_iter)
            children = []
            while child_iter:
                children.append (self.cmds_ts.iter_to_command(child_iter))
                child_iter = model.iter_next (child_iter)

            if not children:
                cell.set_property ("cell-background-set", False)
            else:
                cell.set_property ("cell-background-set", True)

                statuses = [ cmd.status () for cmd in children ]
                
                if all ([s == statuses[0] for s in statuses]):
                    # if all the commands in a group have the same status, then
                    # color them by that status
                    cell.set_property ("cell-background", 
                            color_map[statuses[0]])
                else:
                    # otherwise, color them yellow
                    cell.set_property ("cell-background", "Yellow")

            return

        cell.set_property ("cell-background-set", True)
        cell.set_property ("cell-background", color_map[cmd.status ()])
