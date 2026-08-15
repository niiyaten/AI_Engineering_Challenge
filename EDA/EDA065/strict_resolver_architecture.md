# Strict Resolver architecture

Gate19 uses source requirements, deterministic candidate construction, candidate selection/content verification, then `final_selected_file_ids`. `resolve_source_selection` turns that selected set into a conservative source contract; it does not independently rerank all SearchRecord entries. The tool registry receives this final set, picks a route from the selected file types, and passes it to the capability executor. Human_check is not part of this path.
