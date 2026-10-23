#!/usr/bin/env bash
# Creates DojoFighter.xcodeproj for the native SwiftUI + RealityKit app.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MODELS_DIR="$ROOT/DojoFighter/Resources/Models"
mkdir -p "$MODELS_DIR"
# Xcode needs the folder to exist; add a keep file if empty
if [[ -z "$(ls -A "$MODELS_DIR" 2>/dev/null || true)" ]]; then
  cat > "$MODELS_DIR/README.txt" <<'EOF'
Place fullbody_fighter_arena.usdz and user_hyperrealistic_avatar.usdz here.
Run: Scripts/export_usdz_from_blender.py via Blender (see ../README.md).
EOF
fi

if command -v xcodegen >/dev/null 2>&1; then
  echo "Using xcodegen…"
  xcodegen generate
  echo "Created DojoFighter.xcodeproj"
  exit 0
fi

echo "xcodegen not found — writing a minimal Xcode project with Swift Package tools fallback…"

# Minimal pbxproj generator (macOS app, arm64/x86_64, RealityKit)
PROJECT_DIR="$ROOT/DojoFighter.xcodeproj"
mkdir -p "$PROJECT_DIR"

python3 - <<'PY'
import os, uuid, pathlib

root = pathlib.Path(os.environ.get("ROOT", os.getcwd()))
if not (root / "DojoFighter").exists():
    root = pathlib.Path(".").resolve()

src_root = root / "DojoFighter"
project_dir = root / "DojoFighter.xcodeproj"
project_dir.mkdir(exist_ok=True)

def uid():
    return uuid.uuid4().hex[:24].upper()

# Collect swift files + resources
swift_files = sorted(src_root.rglob("*.swift"))
resource_files = []
for pattern in ("*.usdz", "*.usd", "*.glb", "*.plist", "*.txt", "*.json"):
    resource_files.extend(src_root.rglob(pattern))
# Assets
asset_catalogs = sorted(src_root.rglob("*.xcassets"))

# Stable-ish IDs
ids = {
    "project": uid(),
    "target": uid(),
    "sources": uid(),
    "resources": uid(),
    "frameworks": uid(),
    "product": uid(),
    "native_target": uid(),
    "sources_phase": uid(),
    "resources_phase": uid(),
    "frameworks_phase": uid(),
    "project_config_list": uid(),
    "target_config_list": uid(),
    "debug_project": uid(),
    "release_project": uid(),
    "debug_target": uid(),
    "release_target": uid(),
    "main_group": uid(),
    "products_group": uid(),
    "src_group": uid(),
    "product_ref": uid(),
}

file_entries = []  # (id, path, name, is_source)
build_file_sources = []
build_file_resources = []

def add_file(path: pathlib.Path, is_source: bool):
    fid = uid()
    bid = uid()
    rel = path.relative_to(src_root).as_posix()
    name = path.name
    file_entries.append((fid, rel, name, is_source, path.suffix))
    if is_source:
        build_file_sources.append((bid, fid, name))
    else:
        build_file_resources.append((bid, fid, name))

for p in swift_files:
    add_file(p, True)

# Info.plist is build setting, not necessarily copy
for p in resource_files:
    if p.name == "Info.plist":
        continue
    if p.suffix == ".json" and "Assets.xcassets" in p.as_posix():
        continue
    add_file(p, False)

for p in asset_catalogs:
    fid = uid()
    bid = uid()
    rel = p.relative_to(src_root).as_posix()
    file_entries.append((fid, rel, p.name, False, ".xcassets"))
    build_file_resources.append((bid, fid, p.name))

# Group hierarchy: flatten under DojoFighter group with path DojoFighter
pbx_build_files = []
for bid, fid, name in build_file_sources + build_file_resources:
    pbx_build_files.append(f'\t\t{bid} /* {name} in build */ = {{isa = PBXBuildFile; fileRef = {fid} /* {name} */; }};')

pbx_file_refs = []
for fid, rel, name, is_source, suffix in file_entries:
    last = {
        ".swift": "sourcecode.swift",
        ".usdz": "file.usdz",
        ".usd": "file.usd",
        ".glb": "file",
        ".txt": "text",
        ".plist": "text.plist.xml",
        ".xcassets": "folder.assetcatalog",
        ".json": "text.json",
    }.get(suffix, "file")
    pbx_file_refs.append(
        f'\t\t{fid} /* {name} */ = {{isa = PBXFileReference; lastKnownFileType = {last}; path = "{rel}"; sourceTree = "<group>"; }};'
    )

pbx_file_refs.append(
    f'\t\t{ids["product_ref"]} /* DojoFighter.app */ = {{isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = DojoFighter.app; sourceTree = BUILT_PRODUCTS_DIR; }};'
)

src_children = "\n".join(f"\t\t\t\t{fid} /* {name} */," for fid, rel, name, *_ in file_entries)
source_build = "\n".join(f"\t\t\t\t{bid} /* {name} in Sources */," for bid, fid, name in build_file_sources)
resource_build = "\n".join(f"\t\t\t\t{bid} /* {name} in Resources */," for bid, fid, name in build_file_resources)

# Fix comment labels
source_build = "\n".join(f"\t\t\t\t{bid} /* {name} in Sources */," for bid, fid, name in build_file_sources)
resource_build = "\n".join(f"\t\t\t\t{bid} /* {name} in Resources */," for bid, fid, name in build_file_resources)

info_plist_rel = "DojoFighter/Resources/Info.plist"

content = f'''// !$*UTF8*$!
{{
	archiveVersion = 1;
	classes = {{
	}};
	objectVersion = 56;
	objects = {{

/* Begin PBXBuildFile section */
{chr(10).join(pbx_build_files)}
/* End PBXBuildFile section */

/* Begin PBXFileReference section */
{chr(10).join(pbx_file_refs)}
/* End PBXFileReference section */

/* Begin PBXFrameworksBuildPhase section */
		{ids["frameworks_phase"]} /* Frameworks */ = {{
			isa = PBXFrameworksBuildPhase;
			buildActionMask = 2147483647;
			files = (
			);
			runOnlyForDeploymentPostprocessing = 0;
		}};
/* End PBXFrameworksBuildPhase section */

/* Begin PBXGroup section */
		{ids["main_group"]} = {{
			isa = PBXGroup;
			children = (
				{ids["src_group"]} /* DojoFighter */,
				{ids["products_group"]} /* Products */,
			);
			sourceTree = "<group>";
		}};
		{ids["products_group"]} /* Products */ = {{
			isa = PBXGroup;
			children = (
				{ids["product_ref"]} /* DojoFighter.app */,
			);
			name = Products;
			sourceTree = "<group>";
		}};
		{ids["src_group"]} /* DojoFighter */ = {{
			isa = PBXGroup;
			children = (
{src_children}
			);
			path = DojoFighter;
			sourceTree = "<group>";
		}};
/* End PBXGroup section */

/* Begin PBXNativeTarget section */
		{ids["native_target"]} /* DojoFighter */ = {{
			isa = PBXNativeTarget;
			buildConfigurationList = {ids["target_config_list"]} /* Build configuration list for PBXNativeTarget "DojoFighter" */;
			buildPhases = (
				{ids["sources_phase"]} /* Sources */,
				{ids["frameworks_phase"]} /* Frameworks */,
				{ids["resources_phase"]} /* Resources */,
			);
			buildRules = (
			);
			dependencies = (
			);
			name = DojoFighter;
			productName = DojoFighter;
			productReference = {ids["product_ref"]} /* DojoFighter.app */;
			productType = "com.apple.product-type.application";
		}};
/* End PBXNativeTarget section */

/* Begin PBXProject section */
		{ids["project"]} /* Project object */ = {{
			isa = PBXProject;
			attributes = {{
				BuildIndependentTargetsInParallel = 1;
				LastSwiftUpdateCheck = 1500;
				LastUpgradeCheck = 1500;
			}};
			buildConfigurationList = {ids["project_config_list"]} /* Build configuration list for PBXProject "DojoFighter" */;
			compatibilityVersion = "Xcode 14.0";
			developmentRegion = en;
			hasScannedForEncodings = 0;
			knownRegions = (
				en,
				Base,
			);
			mainGroup = {ids["main_group"]};
			productRefGroup = {ids["products_group"]} /* Products */;
			projectDirPath = "";
			projectRoot = "";
			targets = (
				{ids["native_target"]} /* DojoFighter */,
			);
		}};
/* End PBXProject section */

/* Begin PBXResourcesBuildPhase section */
		{ids["resources_phase"]} /* Resources */ = {{
			isa = PBXResourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
{resource_build}
			);
			runOnlyForDeploymentPostprocessing = 0;
		}};
/* End PBXResourcesBuildPhase section */

/* Begin PBXSourcesBuildPhase section */
		{ids["sources_phase"]} /* Sources */ = {{
			isa = PBXSourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
{source_build}
			);
			runOnlyForDeploymentPostprocessing = 0;
		}};
/* End PBXSourcesBuildPhase section */

/* Begin XCBuildConfiguration section */
		{ids["debug_project"]} /* Debug */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{
				ALWAYS_SEARCH_USER_PATHS = NO;
				CLANG_ENABLE_MODULES = YES;
				COPY_PHASE_STRIP = NO;
				DEBUG_INFORMATION_FORMAT = dwarf;
				GCC_DYNAMIC_NO_PIC = NO;
				MACOSX_DEPLOYMENT_TARGET = 14.0;
				ONLY_ACTIVE_ARCH = YES;
				SDKROOT = macosx;
				SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG;
				SWIFT_OPTIMIZATION_LEVEL = "-Onone";
			}};
			name = Debug;
		}};
		{ids["release_project"]} /* Release */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{
				ALWAYS_SEARCH_USER_PATHS = NO;
				CLANG_ENABLE_MODULES = YES;
				COPY_PHASE_STRIP = NO;
				DEBUG_INFORMATION_FORMAT = "dwarf-with-dsym";
				MACOSX_DEPLOYMENT_TARGET = 14.0;
				SDKROOT = macosx;
				SWIFT_COMPILATION_MODE = wholemodule;
			}};
			name = Release;
		}};
		{ids["debug_target"]} /* Debug */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{
				ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
				CODE_SIGN_IDENTITY = "-";
				CODE_SIGN_STYLE = Automatic;
				COMBINE_HIDPI_IMAGES = YES;
				CURRENT_PROJECT_VERSION = 1;
				ENABLE_HARDENED_RUNTIME = YES;
				GENERATE_INFOPLIST_FILE = NO;
				INFOPLIST_FILE = {info_plist_rel};
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/../Frameworks",
				);
				MACOSX_DEPLOYMENT_TARGET = 14.0;
				MARKETING_VERSION = 1.0;
				PRODUCT_BUNDLE_IDENTIFIER = com.weo.DojoFighter;
				PRODUCT_NAME = "$(TARGET_NAME)";
				SWIFT_EMIT_LOC_STRINGS = YES;
				SWIFT_VERSION = 5.0;
			}};
			name = Debug;
		}};
		{ids["release_target"]} /* Release */ = {{
			isa = XCBuildConfiguration;
			buildSettings = {{
				ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
				CODE_SIGN_IDENTITY = "-";
				CODE_SIGN_STYLE = Automatic;
				COMBINE_HIDPI_IMAGES = YES;
				CURRENT_PROJECT_VERSION = 1;
				ENABLE_HARDENED_RUNTIME = YES;
				GENERATE_INFOPLIST_FILE = NO;
				INFOPLIST_FILE = {info_plist_rel};
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/../Frameworks",
				);
				MACOSX_DEPLOYMENT_TARGET = 14.0;
				MARKETING_VERSION = 1.0;
				PRODUCT_BUNDLE_IDENTIFIER = com.weo.DojoFighter;
				PRODUCT_NAME = "$(TARGET_NAME)";
				SWIFT_EMIT_LOC_STRINGS = YES;
				SWIFT_VERSION = 5.0;
			}};
			name = Release;
		}};
/* End XCBuildConfiguration section */

/* Begin XCConfigurationList section */
		{ids["project_config_list"]} /* Build configuration list for PBXProject "DojoFighter" */ = {{
			isa = XCConfigurationList;
			buildConfigurations = (
				{ids["debug_project"]} /* Debug */,
				{ids["release_project"]} /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		}};
		{ids["target_config_list"]} /* Build configuration list for PBXNativeTarget "DojoFighter" */ = {{
			isa = XCConfigurationList;
			buildConfigurations = (
				{ids["debug_target"]} /* Debug */,
				{ids["release_target"]} /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		}};
/* End XCConfigurationList section */
	}};
	rootObject = {ids["project"]} /* Project object */;
}}
'''

(project_dir / "project.pbxproj").write_text(content)
print(f"Wrote {project_dir / 'project.pbxproj'}")
print(f"Swift files: {len(swift_files)}")
print(f"Resource files: {len(build_file_resources)}")
PY

# workspace shared data
mkdir -p "$PROJECT_DIR/project.xcworkspace"
cat > "$PROJECT_DIR/project.xcworkspace/contents.xcworkspacedata" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<Workspace
   version = "1.0">
   <FileRef
      location = "self:">
   </FileRef>
</Workspace>
EOF

echo "Created $PROJECT_DIR"
echo "Open with: open DojoFighter.xcodeproj"
