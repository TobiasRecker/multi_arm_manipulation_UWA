// Native Gazebo Rendering / Ogre2 offline camera capture. No simulator or ROS.
#include <gz/rendering.hh>
#include <gz/math.hh>
#include <nlohmann/json.hpp>
#include <fstream>
#include <iostream>
#include <filesystem>
#include <map>
#include <stdexcept>

using json = nlohmann::json;
namespace r = gz::rendering;
namespace m = gz::math;

m::Pose3d Pose(const json &v) {
  return {{v[0].get<double>(), v[1].get<double>(), v[2].get<double>()},
          {v[6].get<double>(), v[3].get<double>(), v[4].get<double>(), v[5].get<double>()}};
}
m::Vector3d Vec(const json &v) { return {v[0].get<double>(), v[1].get<double>(), v[2].get<double>()}; }

void Aim(r::CameraPtr camera, const m::Vector3d &eye, const m::Vector3d &target) {
  auto d = target - eye;
  camera->SetLocalPosition(eye);
  camera->SetLocalRotation(0, std::atan2(-d.Z(), std::hypot(d.X(), d.Y())), std::atan2(d.Y(), d.X()));
}

int main(int argc, char **argv) {
  if (argc < 3) { std::cerr << "render_carton MOVIE_JSON OUTPUT [preview]\n"; return 2; }
  try {
    json data; std::ifstream(argv[1]) >> data;
    std::filesystem::path out(argv[2]); std::filesystem::create_directories(out);
    bool preview = argc > 3;
    auto engine = r::engine("ogre2", {{"headless", "1"}});
    if (!engine) throw std::runtime_error("Ogre2 unavailable");
    auto scene = engine->CreateScene("uwa_carton_film");
    scene->SetAmbientLight(.55, .58, .64);
    scene->SetBackgroundColor(.12, .16, .22);
    auto root = scene->RootVisual();
    auto sun = scene->CreateDirectionalLight("soft_key");
    sun->SetDirection(-.4, .2, -.9); sun->SetDiffuseColor(.9, .86, .79);
    sun->SetSpecularColor(.25, .25, .25); sun->SetCastShadows(true); root->AddChild(sun);
    auto fill = scene->CreateDirectionalLight("soft_fill");
    fill->SetDirection(.4, -.7, -.3); fill->SetDiffuseColor(.28, .36, .48);
    fill->SetCastShadows(false); root->AddChild(fill);
    std::map<std::string, r::VisualPtr> nodes; nodes["world"] = root;
    for (auto &name : data["nodes"]) {
      auto node = scene->CreateVisual(name.get<std::string>());
      root->AddChild(node); nodes[name.get<std::string>()] = node;
    }
    size_t materialId = 0;
    for (auto &item : data["visuals"]) {
      auto visual = scene->CreateVisual();
      std::string type = item["shape"];
      r::GeometryPtr geometry;
      if (type == "mesh") {
        std::string path = item["mesh"];
        if (path.rfind("file://", 0) == 0) path.erase(0, 7);
        geometry = scene->CreateMesh(path);
      } else if (type == "box") geometry = scene->CreateBox();
      else if (type == "cylinder") geometry = scene->CreateCylinder();
      else if (type == "sphere") geometry = scene->CreateSphere();
      if (!geometry) throw std::runtime_error("Cannot create visual: " + item.dump());
      visual->AddGeometry(geometry); visual->SetLocalPose(Pose(item["pose"]));
      visual->SetLocalScale(Vec(item["scale"]));
      if (item.contains("color")) {
        auto c = item["color"]; auto mat = scene->CreateMaterial("mat_" + std::to_string(materialId++));
        mat->SetDiffuse(c[0].get<double>(), c[1].get<double>(), c[2].get<double>(), c[3].get<double>());
        mat->SetAmbient(c[0].get<double>(), c[1].get<double>(), c[2].get<double>(), c[3].get<double>());
        mat->SetRoughness(.62); mat->SetMetalness(.05); visual->SetMaterial(mat);
      }
      nodes.at(item["parent"].get<std::string>())->AddChild(visual);
    }
    auto yellow = scene->CreateMaterial("process_yellow");
    yellow->SetDiffuse(1, .78, .025); yellow->SetAmbient(1, .78, .025); yellow->SetEmissive(.55, .34, .005);
    auto red = scene->CreateMaterial("process_red");
    red->SetDiffuse(1, .025, .045); red->SetAmbient(1, .025, .045); red->SetEmissive(.6, .005, .005);
    std::vector<r::VisualPtr> marks;
    for (auto &item : data["traces"]) {
      auto a = Vec(item["a"]), b = Vec(item["b"]), d = b - a;
      bool isRed = item["red"];
      auto visual = scene->CreateVisual(); visual->AddGeometry(scene->CreateCylinder());
      m::Quaterniond rotation; rotation.SetFrom2Axes(m::Vector3d::UnitZ, d.Normalized());
      visual->SetLocalPose({(a + b) * .5, rotation});
      double width = isRed ? .006 : .0036;
      visual->SetLocalScale(width, width, d.Length() + .001);
      visual->SetMaterial(isRed ? red : yellow); visual->SetVisible(false);
      nodes.at("carton")->AddChild(visual); marks.push_back(visual);
      if (isRed) {
        auto dot = scene->CreateVisual(); dot->AddGeometry(scene->CreateSphere());
        dot->SetLocalPosition(a); dot->SetLocalScale(.009); dot->SetMaterial(red); dot->SetVisible(false);
        visual->AddChild(dot);
        // The sphere is a separate carton-local visual; avoid inherited scale.
        visual->RemoveChild(dot); nodes.at("carton")->AddChild(dot);
        // Pair its visibility to the segment in the render loop below.
        marks.back()->SetUserData("dot", int(marks.size()));
      }
    }
    // Red surface dots are created explicitly below to keep state simple.
    std::vector<std::pair<size_t, r::VisualPtr>> dots;
    for (size_t k = 0; k < data["traces"].size(); ++k) if (data["traces"][k]["red"].get<bool>()) {
      auto v = scene->CreateVisual(); v->AddGeometry(scene->CreateSphere()); v->SetLocalPosition(Vec(data["traces"][k]["a"]));
      v->SetLocalScale(.009); v->SetMaterial(red); v->SetVisible(false); nodes.at("carton")->AddChild(v); dots.emplace_back(k, v);
    }
    auto overview = scene->CreateCamera("overview");
    overview->SetImageWidth(1200); overview->SetImageHeight(864); overview->SetAspectRatio(1200. / 864);
    overview->SetHFOV(m::Angle(.92)); overview->SetAntiAliasing(4); overview->SetNearClipPlane(.04); overview->SetFarClipPlane(100);
    root->AddChild(overview);
    auto detail = scene->CreateCamera("detail");
    detail->SetImageWidth(640); detail->SetImageHeight(864); detail->SetAspectRatio(640. / 864);
    detail->SetHFOV(m::Angle(.78)); detail->SetAntiAliasing(4); detail->SetNearClipPlane(.015); detail->SetFarClipPlane(100);
    root->AddChild(detail);
    auto image1 = overview->CreateImage(), image2 = detail->CreateImage();
    std::ofstream stream1, stream2;
    if (!preview) { stream1.open(out / "overview.rgb", std::ios::binary); stream2.open(out / "detail.rgb", std::ios::binary); }
    std::vector<size_t> selected;
    if (preview) {
      for (std::string phase : {"home", "draw_y_max", "draw_z_min_edge_8", "axial_feed_z_min_site_6", "draw_bottom_circle", "draw_y_min", "complete"}) {
        size_t chosen = 0;
        for (size_t i = 0; i < data["frames"].size(); ++i) if (data["frames"][i]["phase"] == phase) chosen = i;
        selected.push_back(chosen);
      }
    } else for (size_t i = 0; i < data["frames"].size(); ++i) selected.push_back(i);
    m::Vector3d detailEye, detailTarget;
    for (size_t index : selected) {
      auto &f = data["frames"][index];
      for (size_t j = 0; j < data["nodes"].size(); ++j) nodes.at(data["nodes"][j].get<std::string>())->SetLocalPose(Pose(f["poses"][j]));
      for (size_t j = 0; j < marks.size(); ++j) marks[j]->SetVisible(data["traces"][j]["born"].get<size_t>() <= index);
      for (auto &[j, dot] : dots) dot->SetVisible(data["traces"][j]["born"].get<size_t>() <= index);
      auto object = Pose(f["object"]);
      auto centre = object.Pos() + object.Rot().RotateVector({.201, .17, .065});
      // Stable overview: three active arms and enough surrounding cell context.
      Aim(overview, {2.85, -3.65, 2.65}, {0., 0., 1.02});
      m::Vector3d normal;
      std::string face = f["face"];
      if (face == "y_max") normal = {0, 1, 0};
      else if (face == "y_min") normal = {0, -1, 0};
      else normal = {0, 0, -1};
      auto desiredEye = centre + object.Rot().RotateVector(normal * .80 + m::Vector3d(.28, 0, .28));
      if (index == 0 || preview) { detailEye = desiredEye; detailTarget = centre; }
      else { detailEye = .93 * detailEye + .07 * desiredEye; detailTarget = .93 * detailTarget + .07 * centre; }
      Aim(detail, detailEye, detailTarget);
      scene->PreRender(); overview->Capture(image1); detail->Capture(image2);
      if (preview) {
        // PPMs are lossless and readable without extra rendering dependencies.
        for (auto pair : {std::make_pair("overview", &image1), std::make_pair("detail", &image2)}) {
          std::ofstream ppm(out / (std::to_string(index) + "-" + pair.first + ".ppm"), std::ios::binary);
          ppm << "P6\n" << pair.second->Width() << ' ' << pair.second->Height() << "\n255\n";
          ppm.write(pair.second->Data<char>(), pair.second->Width() * pair.second->Height() * 3);
        }
      } else {
        stream1.write(image1.Data<char>(), 1200 * 864 * 3);
        stream2.write(image2.Data<char>(), 640 * 864 * 3);
      }
      if (index % 150 == 0 || preview) std::cout << "Rendered " << index << '/' << data["frames"].size() << std::endl;
    }
    scene->Destroy(); engine->Destroy();
    return 0;
  } catch (const std::exception &e) { std::cerr << e.what() << '\n'; return 1; }
}
