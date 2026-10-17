import { useEffect, useState } from "react";
import { api, Course, Package } from "../api";
import { Empty, PageHead } from "../components/ui";
import { kzt, Lang, tr } from "../format";

export function CoursesPage({ lang }: { lang: Lang }) {
  const [courses, setCourses] = useState<Course[]>([]);
  const [packages, setPackages] = useState<Package[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.listCourses(), api.listPackages()])
      .then(([c, p]) => {
        setCourses(c);
        setPackages(p);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Error"));
  }, []);

  const byId = new Map(courses.map((c) => [c.id, c]));
  return (
    <div>
      <PageHead title={tr(lang, "Курсы и пакеты", "Courses and packages")} subtitle={tr(lang, "Каталог Bilim Academy", "Bilim Academy catalogue")} />
      {error && <p className="error">{error}</p>}
      <div className="panel" style={{ marginBottom: "1rem" }}>
        <h3>{tr(lang, "Курсы", "Courses")}</h3>
        {courses.length === 0 ? (
          <Empty text={tr(lang, "Каталог пуст", "Catalogue is empty")} />
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>{tr(lang, "Код", "Code")}</th>
                <th>{tr(lang, "Курс", "Course")}</th>
                <th>{tr(lang, "Описание", "Description")}</th>
                <th className="num">{tr(lang, "Цена", "Price")}</th>
              </tr>
            </thead>
            <tbody>
              {courses.map((c) => (
                <tr key={c.id}>
                  <td className="muted nowrap">{c.code}</td>
                  <td>{c.title}</td>
                  <td className="muted">{c.description || "—"}</td>
                  <td className="num">{kzt(c.price_kzt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className="panel">
        <h3>{tr(lang, "Пакеты", "Packages")}</h3>
        {packages.length === 0 ? (
          <Empty text={tr(lang, "Пакетов нет", "No packages")} />
        ) : (
          <ul className="list-plain">
            {packages.map((p) => (
              <li key={p.id}>
                <span>
                  <strong>{p.title}</strong> <span className="muted">{p.code}</span>
                  <div className="muted" style={{ fontSize: "0.82rem" }}>
                    {p.course_ids.map((id) => byId.get(id)?.title ?? `#${id}`).join(" + ")}
                  </div>
                </span>
                <strong>{kzt(p.price_kzt)}</strong>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
